"""Tests for router.serve() with SQLAlchemy models (consumer perspective)."""

import pytest
import pytest_asyncio
from fastapi import FastAPI, Request
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from fastrest.routers import DefaultRouter, SimpleRouter
from fastrest.test import APIClient
from fastrest.pagination import PageNumberPagination
from fastrest.filters import SearchFilter, OrderingFilter
from fastrest.permissions import IsAuthenticated

from models import Base, Author, Book, Tag, Review


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield engine, session_factory
    await engine.dispose()


def _make_serve_app(router, session_factory, viewsets):
    app = FastAPI()
    app.include_router(router.urls, prefix="/api")

    @app.middleware("http")
    async def inject_session(request: Request, call_next):
        async with session_factory() as session:
            async with session.begin():
                originals = {}
                for vs in viewsets:
                    originals[vs] = vs.__init__

                    def make_patched(original):
                        def patched_init(self, **kwargs):
                            original(self, **kwargs)
                            self._session = session
                        return patched_init

                    vs.__init__ = make_patched(originals[vs])
                try:
                    response = await call_next(request)
                finally:
                    for vs in viewsets:
                        vs.__init__ = originals[vs]
                return response

    return app


class TestServeBasicCRUD:
    """Test serve() creates full CRUD endpoints from raw SQLAlchemy models."""

    @pytest.mark.asyncio
    async def test_full_crud_lifecycle(self, db):
        engine, session_factory = db
        router = DefaultRouter()
        vs = router.serve(Author, prefix="authors")
        app = _make_serve_app(router, session_factory, [vs])
        client = APIClient(app)

        # Create
        resp = await client.post("/api/authors", json={"name": "Jane Austen"})
        assert resp.status_code == 201
        author = resp.json()
        assert author["name"] == "Jane Austen"
        aid = author["id"]

        # Retrieve
        resp = await client.get(f"/api/authors/{aid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Jane Austen"

        # Update
        resp = await client.put(f"/api/authors/{aid}", json={"name": "Jane A.", "is_active": False})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Jane A."

        # Partial update
        resp = await client.patch(f"/api/authors/{aid}", json={"bio": "English novelist"})
        assert resp.status_code == 200
        assert resp.json()["bio"] == "English novelist"

        # List
        resp = await client.get("/api/authors")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

        # Delete
        resp = await client.delete(f"/api/authors/{aid}")
        assert resp.status_code == 204

        # Confirm deleted
        resp = await client.get(f"/api/authors/{aid}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_serve_multiple_models(self, db):
        engine, session_factory = db
        router = DefaultRouter()
        vs_a = router.serve(Author, prefix="authors")
        vs_t = router.serve(Tag, prefix="tags")
        app = _make_serve_app(router, session_factory, [vs_a, vs_t])
        client = APIClient(app)

        resp = await client.post("/api/authors", json={"name": "Author1"})
        assert resp.status_code == 201

        resp = await client.post("/api/tags", json={"name": "fiction", "slug": "fiction"})
        assert resp.status_code == 201

        resp = await client.get("/api/authors")
        assert len(resp.json()) == 1

        resp = await client.get("/api/tags")
        assert len(resp.json()) == 1


class TestServeReadonly:
    @pytest.mark.asyncio
    async def test_readonly_blocks_writes(self, db):
        engine, session_factory = db
        router = DefaultRouter()
        vs = router.serve(Author, prefix="authors", readonly=True)
        app = _make_serve_app(router, session_factory, [vs])
        client = APIClient(app)

        resp = await client.post("/api/authors", json={"name": "Test"})
        assert resp.status_code == 405

    @pytest.mark.asyncio
    async def test_readonly_allows_reads(self, db):
        engine, session_factory = db
        router = DefaultRouter()
        vs = router.serve(Author, prefix="authors", readonly=True)
        app = _make_serve_app(router, session_factory, [vs])
        client = APIClient(app)

        resp = await client.get("/api/authors")
        assert resp.status_code == 200


class TestServeFieldOptions:
    @pytest.mark.asyncio
    async def test_fields_whitelist(self, db):
        engine, session_factory = db
        router = DefaultRouter()
        vs = router.serve(Author, prefix="authors", fields=["id", "name"])
        app = _make_serve_app(router, session_factory, [vs])
        client = APIClient(app)

        resp = await client.post("/api/authors", json={"name": "Test"})
        assert resp.status_code == 201
        data = resp.json()
        assert "name" in data
        assert "bio" not in data
        assert "is_active" not in data

    @pytest.mark.asyncio
    async def test_exclude_fields(self, db):
        engine, session_factory = db
        router = DefaultRouter()
        vs = router.serve(Author, prefix="authors", exclude=["bio"])
        app = _make_serve_app(router, session_factory, [vs])
        client = APIClient(app)

        resp = await client.post("/api/authors", json={"name": "Test"})
        assert resp.status_code == 201
        data = resp.json()
        assert "name" in data
        assert "bio" not in data


class TestServePagination:
    @pytest.mark.asyncio
    async def test_page_number_pagination(self, db):
        engine, session_factory = db

        class TinyPage(PageNumberPagination):
            page_size = 2

        router = DefaultRouter()
        vs = router.serve(Author, prefix="authors", pagination_class=TinyPage)
        app = _make_serve_app(router, session_factory, [vs])
        client = APIClient(app)

        for i in range(5):
            await client.post("/api/authors", json={"name": f"Author {i}"})

        resp = await client.get("/api/authors?page=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 5
        assert len(data["results"]) == 2
        assert data["next"] is not None


class TestServeFiltering:
    @pytest.mark.asyncio
    async def test_search_filter(self, db):
        engine, session_factory = db
        router = DefaultRouter()
        vs = router.serve(
            Author, prefix="authors",
            filter_backends=[SearchFilter],
            search_fields=["name", "bio"],
        )
        app = _make_serve_app(router, session_factory, [vs])
        client = APIClient(app)

        await client.post("/api/authors", json={"name": "Alice", "bio": "Writer"})
        await client.post("/api/authors", json={"name": "Bob", "bio": "Painter"})

        resp = await client.get("/api/authors?search=Alice")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_ordering_filter(self, db):
        engine, session_factory = db
        router = DefaultRouter()
        vs = router.serve(
            Author, prefix="authors",
            filter_backends=[OrderingFilter],
            ordering_fields=["name"],
        )
        app = _make_serve_app(router, session_factory, [vs])
        client = APIClient(app)

        await client.post("/api/authors", json={"name": "Zara"})
        await client.post("/api/authors", json={"name": "Alice"})

        resp = await client.get("/api/authors?ordering=name")
        names = [a["name"] for a in resp.json()]
        assert names == ["Alice", "Zara"]

        resp = await client.get("/api/authors?ordering=-name")
        names = [a["name"] for a in resp.json()]
        assert names == ["Zara", "Alice"]


class TestServeOpenAPI:
    @pytest.mark.asyncio
    async def test_serve_openapi_endpoints(self, db):
        engine, session_factory = db
        router = DefaultRouter()
        vs = router.serve(Author, prefix="authors")
        app = _make_serve_app(router, session_factory, [vs])
        client = APIClient(app)

        resp = await client.get("/openapi.json")
        assert resp.status_code == 200
        paths = resp.json()["paths"]
        assert "/api/authors" in paths
        assert "/api/authors/{pk}" in paths

    @pytest.mark.asyncio
    async def test_serve_readonly_openapi(self, db):
        engine, session_factory = db
        router = DefaultRouter()
        vs = router.serve(Author, prefix="authors", readonly=True)
        app = _make_serve_app(router, session_factory, [vs])
        client = APIClient(app)

        resp = await client.get("/openapi.json")
        paths = resp.json()["paths"]
        assert "post" not in paths.get("/api/authors", {})
        assert "put" not in paths.get("/api/authors/{pk}", {})
        assert "delete" not in paths.get("/api/authors/{pk}", {})
