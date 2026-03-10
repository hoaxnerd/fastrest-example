"""Tests for router.serve() with SQLModel models (consumer perspective)."""

import pytest
import pytest_asyncio
from fastapi import FastAPI, Request
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from fastrest.routers import DefaultRouter
from fastrest.compat.orm import set_default_adapter, reset_default_adapter
from fastrest.compat.orm.sqlmodel import SQLModelAdapter
from fastrest.test import APIClient
from fastrest.pagination import PageNumberPagination
from fastrest.filters import SearchFilter, OrderingFilter

from tests_sqlmodel.models import SMAuthor, SMBook, SMTag


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
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


class TestServeSQLModel:
    @pytest.mark.asyncio
    async def test_full_crud(self, db):
        engine, session_factory = db
        set_default_adapter(SQLModelAdapter())
        try:
            router = DefaultRouter()
            vs = router.serve(SMAuthor, prefix="authors")
            app = _make_serve_app(router, session_factory, [vs])
            client = APIClient(app)

            # Create
            resp = await client.post("/api/authors", json={"name": "Test Author"})
            assert resp.status_code == 201
            aid = resp.json()["id"]

            # Retrieve
            resp = await client.get(f"/api/authors/{aid}")
            assert resp.status_code == 200
            assert resp.json()["name"] == "Test Author"

            # List
            resp = await client.get("/api/authors")
            assert resp.status_code == 200
            assert len(resp.json()) >= 1

            # Update
            resp = await client.put(f"/api/authors/{aid}", json={"name": "Updated"})
            assert resp.status_code == 200

            # Delete
            resp = await client.delete(f"/api/authors/{aid}")
            assert resp.status_code == 204
        finally:
            reset_default_adapter()

    @pytest.mark.asyncio
    async def test_serve_multiple_models(self, db):
        engine, session_factory = db
        set_default_adapter(SQLModelAdapter())
        try:
            router = DefaultRouter()
            vs_a = router.serve(SMAuthor, prefix="authors")
            vs_t = router.serve(SMTag, prefix="tags")
            app = _make_serve_app(router, session_factory, [vs_a, vs_t])
            client = APIClient(app)

            resp = await client.post("/api/authors", json={"name": "A1"})
            assert resp.status_code == 201

            resp = await client.post("/api/tags", json={"name": "t1", "slug": "t1"})
            assert resp.status_code == 201
        finally:
            reset_default_adapter()

    @pytest.mark.asyncio
    async def test_serve_readonly(self, db):
        engine, session_factory = db
        set_default_adapter(SQLModelAdapter())
        try:
            router = DefaultRouter()
            vs = router.serve(SMAuthor, prefix="authors", readonly=True)
            app = _make_serve_app(router, session_factory, [vs])
            client = APIClient(app)

            resp = await client.post("/api/authors", json={"name": "Test"})
            assert resp.status_code == 405

            resp = await client.get("/api/authors")
            assert resp.status_code == 200
        finally:
            reset_default_adapter()

    @pytest.mark.asyncio
    async def test_serve_with_search(self, db):
        engine, session_factory = db
        set_default_adapter(SQLModelAdapter())
        try:
            router = DefaultRouter()
            vs = router.serve(
                SMAuthor, prefix="authors",
                filter_backends=[SearchFilter],
                search_fields=["name"],
            )
            app = _make_serve_app(router, session_factory, [vs])
            client = APIClient(app)

            await client.post("/api/authors", json={"name": "Alice"})
            await client.post("/api/authors", json={"name": "Bob"})

            resp = await client.get("/api/authors?search=Alice")
            assert resp.status_code == 200
            assert len(resp.json()) == 1
        finally:
            reset_default_adapter()

    @pytest.mark.asyncio
    async def test_serve_with_pagination(self, db):
        engine, session_factory = db
        set_default_adapter(SQLModelAdapter())
        try:
            class TinyPage(PageNumberPagination):
                page_size = 2

            router = DefaultRouter()
            vs = router.serve(SMAuthor, prefix="authors", pagination_class=TinyPage)
            app = _make_serve_app(router, session_factory, [vs])
            client = APIClient(app)

            for i in range(5):
                await client.post("/api/authors", json={"name": f"Author {i}"})

            resp = await client.get("/api/authors?page=1")
            assert resp.status_code == 200
            data = resp.json()
            assert data["count"] == 5
            assert len(data["results"]) == 2
        finally:
            reset_default_adapter()

    @pytest.mark.asyncio
    async def test_serve_fields_whitelist(self, db):
        engine, session_factory = db
        set_default_adapter(SQLModelAdapter())
        try:
            router = DefaultRouter()
            vs = router.serve(SMAuthor, prefix="authors", fields=["id", "name"])
            app = _make_serve_app(router, session_factory, [vs])
            client = APIClient(app)

            resp = await client.post("/api/authors", json={"name": "Test"})
            assert resp.status_code == 201
            data = resp.json()
            assert "name" in data
            assert "bio" not in data
        finally:
            reset_default_adapter()
