"""Tests for router.serve() with Tortoise ORM models (consumer perspective)."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from tortoise import Tortoise

from fastrest.routers import DefaultRouter
from fastrest.compat.orm import set_default_adapter, reset_default_adapter
from fastrest.compat.orm.tortoise import TortoiseAdapter
from fastrest.test import APIClient
from fastrest.pagination import PageNumberPagination
from fastrest.filters import SearchFilter, OrderingFilter

from tests_tortoise.models import TAuthor, TTag


@pytest_asyncio.fixture
async def tortoise_db():
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["tests_tortoise.models"]},
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


class TestServeTortoise:
    @pytest.mark.asyncio
    async def test_full_crud(self, tortoise_db):
        set_default_adapter(TortoiseAdapter())
        try:
            router = DefaultRouter()
            vs = router.serve(TAuthor, prefix="authors")
            app = FastAPI()
            app.include_router(router.urls, prefix="/api")
            client = APIClient(app)

            # Create
            resp = await client.post("/api/authors", json={"name": "Tortoise Author"})
            assert resp.status_code == 201
            aid = resp.json()["id"]

            # Retrieve
            resp = await client.get(f"/api/authors/{aid}")
            assert resp.status_code == 200
            assert resp.json()["name"] == "Tortoise Author"

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
    async def test_serve_readonly(self, tortoise_db):
        set_default_adapter(TortoiseAdapter())
        try:
            router = DefaultRouter()
            vs = router.serve(TAuthor, prefix="authors", readonly=True)
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
    async def test_serve_multiple_models(self, tortoise_db):
        set_default_adapter(TortoiseAdapter())
        try:
            router = DefaultRouter()
            vs_a = router.serve(TAuthor, prefix="authors")
            vs_t = router.serve(TTag, prefix="tags")
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
    async def test_serve_with_search(self, tortoise_db):
        set_default_adapter(TortoiseAdapter())
        try:
            router = DefaultRouter()
            vs = router.serve(
                TAuthor, prefix="authors",
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
    async def test_serve_with_pagination(self, tortoise_db):
        set_default_adapter(TortoiseAdapter())
        try:
            class TinyPage(PageNumberPagination):
                page_size = 2

            router = DefaultRouter()
            vs = router.serve(TAuthor, prefix="authors", pagination_class=TinyPage)
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

    @pytest.mark.asyncio
    async def test_serve_fields_whitelist(self, tortoise_db):
        set_default_adapter(TortoiseAdapter())
        try:
            router = DefaultRouter()
            vs = router.serve(TAuthor, prefix="authors", fields=["id", "name"])
            app = FastAPI()
            app.include_router(router.urls, prefix="/api")
            client = APIClient(app)

            resp = await client.post("/api/authors", json={"name": "Test"})
            assert resp.status_code == 201
            data = resp.json()
            assert "name" in data
            assert "bio" not in data
        finally:
            reset_default_adapter()
