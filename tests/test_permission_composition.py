"""Tests for permission composition with &, |, ~ operators."""

import pytest
import pytest_asyncio
from fastapi import FastAPI, Request
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from fastrest.routers import DefaultRouter
from fastrest.viewsets import ModelViewSet
from fastrest.serializers import ModelSerializer
from fastrest.permissions import (
    BasePermission, IsAuthenticated, IsAdminUser,
    IsAuthenticatedOrReadOnly, AllowAny, HasScope,
)
from fastrest.authentication import TokenAuthentication
from fastrest.test import APIClient

from models import Base, Author


# ── Auth setup ──────────────────────────────────────────────────────

class FakeUser:
    def __init__(self, id, is_staff=False):
        self.id = id
        self.is_staff = is_staff
    def __bool__(self):
        return True

class ScopedAuth:
    """Auth token with scopes — HasScope reads from request.auth.scopes."""
    def __init__(self, scopes=None):
        self.scopes = scopes or []

# TokenAuthentication returns (user, auth). HasScope reads auth.scopes.
# To make scopes work, we use a custom auth backend that returns ScopedAuth.
class ScopedTokenAuth(BasePermission):
    """Not a real auth — just a test helper."""
    pass

TOKEN_DATA = {
    "admin-tok": (FakeUser(1, is_staff=True), ScopedAuth(["write", "admin"])),
    "editor-tok": (FakeUser(2, is_staff=False), ScopedAuth(["write"])),
    "viewer-tok": (FakeUser(3, is_staff=False), ScopedAuth(["read"])),
}

# Use a custom authentication backend that returns scoped auth objects
from fastrest.authentication import BaseAuthentication, AuthenticationFailed

class ScopedTokenAuthentication(BaseAuthentication):
    """Token auth that returns (user, ScopedAuth) so HasScope works."""
    def authenticate(self, request):
        header = request.headers.get("authorization", "")
        if not header.startswith("Bearer "):
            return None
        key = header.split(" ", 1)[1].strip()
        result = TOKEN_DATA.get(key)
        if result is None:
            raise AuthenticationFailed("Invalid token.")
        return result

    def authenticate_header(self, request):
        return "Bearer"

tok_auth = ScopedTokenAuthentication()


# ── Custom permission ───────────────────────────────────────────────

class IsOwnerById(BasePermission):
    """Check owner_id matches user.id on the object."""
    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return getattr(obj, "id", None) == getattr(request.user, "id", None)


# ── Serializer ──────────────────────────────────────────────────────

class AuthorSer(ModelSerializer):
    class Meta:
        model = Author
        fields = ["id", "name", "bio", "is_active"]
        read_only_fields = ["id"]


# ── Fixture ─────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield engine, sf
    await engine.dispose()


def _make_app(viewset_cls, db):
    engine, sf = db
    router = DefaultRouter()
    router.register("items", viewset_cls, basename="item")
    app = FastAPI()
    app.include_router(router.urls, prefix="/api")

    @app.middleware("http")
    async def inject(request: Request, call_next):
        async with sf() as session:
            async with session.begin():
                orig = viewset_cls.__init__
                def patched(self, **kw):
                    orig(self, **kw)
                    self._session = session
                viewset_cls.__init__ = patched
                try:
                    resp = await call_next(request)
                finally:
                    viewset_cls.__init__ = orig
                return resp
    return app


# ── Tests ───────────────────────────────────────────────────────────

class TestAndComposition:
    """Test IsAuthenticated() & IsAdminUser()."""

    @pytest.mark.asyncio
    async def test_and_both_pass(self, db):
        class VS(ModelViewSet):
            queryset = Author
            serializer_class = AuthorSer
            authentication_classes = [tok_auth]
            permission_classes = [IsAuthenticated() & IsAdminUser()]

        client = APIClient(_make_app(VS, db))
        resp = await client.get("/api/items", headers={"Authorization": "Bearer admin-tok"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_and_right_fails(self, db):
        class VS(ModelViewSet):
            queryset = Author
            serializer_class = AuthorSer
            authentication_classes = [tok_auth]
            permission_classes = [IsAuthenticated() & IsAdminUser()]

        client = APIClient(_make_app(VS, db))
        # editor is authenticated but not admin
        resp = await client.get("/api/items", headers={"Authorization": "Bearer editor-tok"})
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_and_no_auth(self, db):
        class VS(ModelViewSet):
            queryset = Author
            serializer_class = AuthorSer
            authentication_classes = [tok_auth]
            permission_classes = [IsAuthenticated() & IsAdminUser()]

        client = APIClient(_make_app(VS, db))
        resp = await client.get("/api/items")
        assert resp.status_code == 401


class TestOrComposition:
    """Test IsAdminUser() | IsOwnerById()."""

    @pytest.mark.asyncio
    async def test_or_left_passes(self, db):
        class VS(ModelViewSet):
            queryset = Author
            serializer_class = AuthorSer
            authentication_classes = [tok_auth]
            permission_classes = [IsAuthenticated() & (IsAdminUser() | AllowAny())]

        client = APIClient(_make_app(VS, db))
        # admin passes via IsAdminUser
        resp = await client.get("/api/items", headers={"Authorization": "Bearer admin-tok"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_or_right_passes(self, db):
        class VS(ModelViewSet):
            queryset = Author
            serializer_class = AuthorSer
            authentication_classes = [tok_auth]
            permission_classes = [IsAuthenticated() & (IsAdminUser() | AllowAny())]

        client = APIClient(_make_app(VS, db))
        # editor passes via AllowAny
        resp = await client.get("/api/items", headers={"Authorization": "Bearer editor-tok"})
        assert resp.status_code == 200


class TestNestedComposition:
    """Test IsAuthenticatedOrReadOnly() & (IsOwner() | IsAdminUser())."""

    @pytest.mark.asyncio
    async def test_nested_anon_read_allowed(self, db):
        class VS(ModelViewSet):
            queryset = Author
            serializer_class = AuthorSer
            authentication_classes = [tok_auth]
            permission_classes = [IsAuthenticatedOrReadOnly() & (AllowAny() | IsAdminUser())]

        client = APIClient(_make_app(VS, db))
        # Anonymous GET should pass (IsAuthenticatedOrReadOnly allows reads)
        resp = await client.get("/api/items")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_nested_anon_write_blocked(self, db):
        class VS(ModelViewSet):
            queryset = Author
            serializer_class = AuthorSer
            authentication_classes = [tok_auth]
            permission_classes = [IsAuthenticatedOrReadOnly() & (AllowAny() | IsAdminUser())]

        client = APIClient(_make_app(VS, db))
        # Anonymous POST should be blocked
        resp = await client.post("/api/items", json={"name": "Test"})
        assert resp.status_code == 401


class TestHasScope:
    """Test HasScope permission with composed permissions."""

    @pytest.mark.asyncio
    async def test_has_scope_pass(self, db):
        class VS(ModelViewSet):
            queryset = Author
            serializer_class = AuthorSer
            authentication_classes = [tok_auth]
            permission_classes = [IsAuthenticated() & HasScope("write")]

        client = APIClient(_make_app(VS, db))
        resp = await client.get("/api/items", headers={"Authorization": "Bearer editor-tok"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_has_scope_fail(self, db):
        class VS(ModelViewSet):
            queryset = Author
            serializer_class = AuthorSer
            authentication_classes = [tok_auth]
            permission_classes = [IsAuthenticated() & HasScope("admin")]

        client = APIClient(_make_app(VS, db))
        # editor doesn't have 'admin' scope
        resp = await client.get("/api/items", headers={"Authorization": "Bearer editor-tok"})
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_has_scope_with_or(self, db):
        class VS(ModelViewSet):
            queryset = Author
            serializer_class = AuthorSer
            authentication_classes = [tok_auth]
            permission_classes = [IsAuthenticated() & (HasScope("admin") | HasScope("write"))]

        client = APIClient(_make_app(VS, db))
        # editor has 'write' scope, passes via OR
        resp = await client.get("/api/items", headers={"Authorization": "Bearer editor-tok"})
        assert resp.status_code == 200
