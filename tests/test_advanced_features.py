"""Tests for advanced features: multiple auth backends, scopes, throttle strategies,
LimitOffsetPagination, @action with mcp=False, and full app configuration."""

import pytest
import pytest_asyncio
from fastapi import FastAPI, Request
from sqlalchemy import Column, Integer, String, Text, Boolean
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from fastrest.routers import DefaultRouter
from fastrest.viewsets import ModelViewSet, ReadOnlyModelViewSet
from fastrest.serializers import ModelSerializer
from fastrest.decorators import action
from fastrest.response import Response
from fastrest.permissions import IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly, HasScope
from fastrest.authentication import TokenAuthentication, BasicAuthentication
from fastrest.throttling import AnonRateThrottle, UserRateThrottle
from fastrest.pagination import LimitOffsetPagination
from fastrest.filters import SearchFilter, OrderingFilter
from fastrest.settings import configure
from fastrest.test import APIClient

from models import Base, Author


# ── Auth ────────────────────────────────────────────────────────────

class User:
    def __init__(self, id, username, is_staff=False, scopes=None):
        self.id = id
        self.username = username
        self.is_staff = is_staff
        self.scopes = scopes or []
    def __bool__(self):
        return True

TOKENS = {
    "admin-key": User(1, "admin", is_staff=True, scopes=["read", "write", "admin"]),
    "writer-key": User(2, "writer", scopes=["read", "write"]),
    "reader-key": User(3, "reader", scopes=["read"]),
}

def tok_lookup(key):
    return TOKENS.get(key)

def basic_lookup(username, password):
    if username == "admin" and password == "secret":
        return TOKENS["admin-key"]
    return None

tok_auth = TokenAuthentication(get_user_by_token=tok_lookup, keyword="Bearer")
basic_auth = BasicAuthentication(get_user_by_credentials=basic_lookup)


# ── Serializer ──────────────────────────────────────────────────────

class AuthorSer(ModelSerializer):
    class Meta:
        model = Author
        fields = ["id", "name", "bio", "is_active"]
        read_only_fields = ["id"]


# ── Fixtures ────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield engine, sf
    await engine.dispose()


def _make_app(router, sf, viewsets, settings=None):
    app = FastAPI()
    if settings:
        configure(app, settings)
    app.include_router(router.urls, prefix="/api")

    @app.middleware("http")
    async def inject(request: Request, call_next):
        async with sf() as session:
            async with session.begin():
                originals = {}
                for vs in viewsets:
                    originals[vs] = vs.__init__
                    def make_patched(original):
                        def patched_init(self, **kw):
                            original(self, **kw)
                            self._session = session
                        return patched_init
                    vs.__init__ = make_patched(originals[vs])
                try:
                    resp = await call_next(request)
                finally:
                    for vs in viewsets:
                        vs.__init__ = originals[vs]
                return resp
    return app


# ── Tests ───────────────────────────────────────────────────────────

class TestMultipleAuthBackends:
    """Test that both token and basic auth work on the same viewset."""

    @pytest.mark.asyncio
    async def test_token_auth(self, db):
        engine, sf = db
        class VS(ModelViewSet):
            queryset = Author
            serializer_class = AuthorSer
            authentication_classes = [tok_auth, basic_auth]
            permission_classes = [IsAuthenticated()]

        router = DefaultRouter()
        router.register("items", VS, basename="item")
        client = APIClient(_make_app(router, sf, [VS]))

        resp = await client.get("/api/items", headers={"Authorization": "Bearer admin-key"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_basic_auth(self, db):
        import base64
        engine, sf = db
        class VS(ModelViewSet):
            queryset = Author
            serializer_class = AuthorSer
            authentication_classes = [tok_auth, basic_auth]
            permission_classes = [IsAuthenticated()]

        router = DefaultRouter()
        router.register("items", VS, basename="item")
        client = APIClient(_make_app(router, sf, [VS]))

        creds = base64.b64encode(b"admin:secret").decode()
        resp = await client.get("/api/items", headers={"Authorization": f"Basic {creds}"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_no_auth_returns_401(self, db):
        engine, sf = db
        class VS(ModelViewSet):
            queryset = Author
            serializer_class = AuthorSer
            authentication_classes = [tok_auth, basic_auth]
            permission_classes = [IsAuthenticated()]

        router = DefaultRouter()
        router.register("items", VS, basename="item")
        client = APIClient(_make_app(router, sf, [VS]))

        resp = await client.get("/api/items")
        assert resp.status_code == 401


class TestLimitOffsetPagination:
    """Test LimitOffsetPagination style."""

    @pytest.mark.asyncio
    async def test_limit_offset(self, db):
        engine, sf = db

        class SmallLimitOffset(LimitOffsetPagination):
            default_limit = 2
            max_limit = 10

        class VS(ModelViewSet):
            queryset = Author
            serializer_class = AuthorSer
            pagination_class = SmallLimitOffset

        router = DefaultRouter()
        router.register("items", VS, basename="item")
        client = APIClient(_make_app(router, sf, [VS]))

        for i in range(5):
            await client.post("/api/items", json={"name": f"Author {i}"})

        resp = await client.get("/api/items?limit=2&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 5
        assert len(data["results"]) == 2

        resp = await client.get("/api/items?limit=2&offset=2")
        data = resp.json()
        assert len(data["results"]) == 2

        resp = await client.get("/api/items?limit=2&offset=4")
        data = resp.json()
        assert len(data["results"]) == 1


class TestCustomActionWithMcp:
    """Test @action(mcp=False) and @action(mcp_description=...)."""

    @pytest.mark.asyncio
    async def test_action_mcp_false_still_works_via_http(self, db):
        engine, sf = db

        class VS(ModelViewSet):
            queryset = Author
            serializer_class = AuthorSer

            @action(methods=["get"], detail=False, url_path="public-action")
            async def public_action(self, request, **kwargs):
                return Response(data={"msg": "visible"})

            @action(methods=["get"], detail=False, url_path="hidden-action", mcp=False)
            async def hidden_action(self, request, **kwargs):
                return Response(data={"msg": "hidden from MCP but works via HTTP"})

        router = DefaultRouter()
        router.register("items", VS, basename="item")
        client = APIClient(_make_app(router, sf, [VS]))

        # Both actions work via HTTP
        resp = await client.get("/api/items/public-action")
        assert resp.status_code == 200
        assert resp.json()["msg"] == "visible"

        resp = await client.get("/api/items/hidden-action")
        assert resp.status_code == 200
        assert resp.json()["msg"] == "hidden from MCP but works via HTTP"


class TestAppConfiguration:
    """Test configure() with SKILL and MCP settings."""

    @pytest.mark.asyncio
    async def test_skill_md_with_config(self, db):
        engine, sf = db
        vs = type("VS", (ModelViewSet,), {
            "queryset": Author,
            "serializer_class": AuthorSer,
        })

        router = DefaultRouter()
        router.register("items", vs, basename="item")
        client = APIClient(_make_app(router, sf, [vs], settings={
            "SKILL_NAME": "test-api",
            "SKILL_BASE_URL": "http://test.example.com/api",
            "SKILL_DESCRIPTION": "A test API for validation.",
        }))

        resp = await client.get("/api/SKILL.md")
        assert resp.status_code == 200
        content = resp.text
        assert "test-api" in content
        assert "test.example.com" in content

    @pytest.mark.asyncio
    async def test_manifest_with_config(self, db):
        engine, sf = db
        vs = type("VS", (ModelViewSet,), {
            "queryset": Author,
            "serializer_class": AuthorSer,
        })

        router = DefaultRouter()
        router.register("items", vs, basename="item")
        client = APIClient(_make_app(router, sf, [vs], settings={
            "SKILL_NAME": "test-api",
        }))

        resp = await client.get("/api/manifest.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "test-api"
        assert "resources" in data
        assert len(data["resources"]) == 1
        assert data["resources"][0]["name"] == "item"


class TestReadOnlyViewSet:
    """Test ReadOnlyModelViewSet — only GET, no POST/PUT/DELETE."""

    @pytest.mark.asyncio
    async def test_readonly_viewset(self, db):
        engine, sf = db

        class VS(ReadOnlyModelViewSet):
            queryset = Author
            serializer_class = AuthorSer

        router = DefaultRouter()
        router.register("items", VS, basename="item")
        client = APIClient(_make_app(router, sf, [VS]))

        resp = await client.get("/api/items")
        assert resp.status_code == 200

        resp = await client.post("/api/items", json={"name": "Test"})
        assert resp.status_code == 405

    @pytest.mark.asyncio
    async def test_readonly_viewset_openapi(self, db):
        engine, sf = db

        class VS(ReadOnlyModelViewSet):
            queryset = Author
            serializer_class = AuthorSer

        router = DefaultRouter()
        router.register("items", VS, basename="item")
        client = APIClient(_make_app(router, sf, [VS]))

        resp = await client.get("/openapi.json")
        paths = resp.json()["paths"]
        # List and detail should be GET only
        assert "get" in paths.get("/api/items", {})
        assert "post" not in paths.get("/api/items", {})
        if "/api/items/{pk}" in paths:
            assert "get" in paths["/api/items/{pk}"]
            assert "put" not in paths["/api/items/{pk}"]
            assert "delete" not in paths["/api/items/{pk}"]
