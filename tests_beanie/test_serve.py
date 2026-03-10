"""Tests for router.serve() with Beanie models (consumer perspective)."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient

from fastrest.routers import DefaultRouter
from fastrest.compat.orm import set_default_adapter, reset_default_adapter
from fastrest.compat.orm.beanie import BeanieAdapter
from fastrest.test import APIClient
from fastrest.pagination import PageNumberPagination
from fastrest.filters import SearchFilter

from tests_beanie.models import BAuthor, BTag


@pytest_asyncio.fixture
async def beanie_db():
    client = AsyncMongoMockClient()
    await init_beanie(
        database=client.testdb,
        document_models=[BAuthor, BTag],
    )
    yield
    for model in [BAuthor, BTag]:
        await model.delete_all()


class TestServeBeanie:
    @pytest.mark.asyncio
    async def test_full_crud(self, beanie_db):
        set_default_adapter(BeanieAdapter())
        try:
            router = DefaultRouter()
            vs = router.serve(BAuthor, prefix="authors")
            # Verify string PK auto-detection
            assert vs.lookup_field_type is str

            app = FastAPI()
            app.include_router(router.urls, prefix="/api")
            client = APIClient(app)

            # Create
            resp = await client.post("/api/authors", json={"name": "Beanie Author"})
            assert resp.status_code == 201
            aid = resp.json()["id"]
            assert isinstance(aid, str)  # MongoDB ObjectId as string

            # Retrieve
            resp = await client.get(f"/api/authors/{aid}")
            assert resp.status_code == 200
            assert resp.json()["name"] == "Beanie Author"

            # List
            resp = await client.get("/api/authors")
            assert resp.status_code == 200
            assert len(resp.json()) >= 1

            # Update
            resp = await client.put(f"/api/authors/{aid}", json={"name": "Updated"})
            assert resp.status_code == 200
            assert resp.json()["name"] == "Updated"

            # Delete
            resp = await client.delete(f"/api/authors/{aid}")
            assert resp.status_code == 204
        finally:
            reset_default_adapter()

    @pytest.mark.asyncio
    async def test_serve_readonly(self, beanie_db):
        set_default_adapter(BeanieAdapter())
        try:
            router = DefaultRouter()
            vs = router.serve(BAuthor, prefix="authors", readonly=True)
            app = FastAPI()
            app.include_router(router.urls, prefix="/api")
            client = APIClient(app)

            resp = await client.post("/api/authors", json={"name": "Test"})
            assert resp.status_code == 405

            resp = await client.get("/api/authors")
            assert resp.status_code == 200
        finally:
            reset_default_adapter()

    @pytest.mark.asyncio
    async def test_serve_multiple_models(self, beanie_db):
        set_default_adapter(BeanieAdapter())
        try:
            router = DefaultRouter()
            vs_a = router.serve(BAuthor, prefix="authors")
            vs_t = router.serve(BTag, prefix="tags")
            app = FastAPI()
            app.include_router(router.urls, prefix="/api")
            client = APIClient(app)

            resp = await client.post("/api/authors", json={"name": "A1"})
            assert resp.status_code == 201

            resp = await client.post("/api/tags", json={"name": "t1", "slug": "t1"})
            assert resp.status_code == 201
        finally:
            reset_default_adapter()

    @pytest.mark.asyncio
    async def test_serve_with_search(self, beanie_db):
        set_default_adapter(BeanieAdapter())
        try:
            router = DefaultRouter()
            vs = router.serve(
                BAuthor, prefix="authors",
                filter_backends=[SearchFilter],
                search_fields=["name"],
            )
            app = FastAPI()
            app.include_router(router.urls, prefix="/api")
            client = APIClient(app)

            await client.post("/api/authors", json={"name": "Alice"})
            await client.post("/api/authors", json={"name": "Bob"})

            resp = await client.get("/api/authors?search=Alice")
            assert resp.status_code == 200
            assert len(resp.json()) == 1
        finally:
            reset_default_adapter()

    @pytest.mark.asyncio
    async def test_serve_with_pagination(self, beanie_db):
        set_default_adapter(BeanieAdapter())
        try:
            class TinyPage(PageNumberPagination):
                page_size = 2

            router = DefaultRouter()
            vs = router.serve(BAuthor, prefix="authors", pagination_class=TinyPage)
            app = FastAPI()
            app.include_router(router.urls, prefix="/api")
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
