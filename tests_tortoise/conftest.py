"""Test fixtures for the Tortoise ORM bookstore example."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from tortoise import Tortoise

from fastrest.routers import DefaultRouter
from fastrest.compat.orm import set_default_adapter, reset_default_adapter
from fastrest.compat.orm.tortoise import TortoiseAdapter
from fastrest.test import APIClient

from tests_tortoise.views import (
    TAuthorViewSet, TBookViewSet, TTagViewSet, TReviewViewSet,
)


@pytest_asyncio.fixture
async def tortoise_app():
    """Fully wired FastAPI app with Tortoise ORM — no session middleware needed."""
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["tests_tortoise.models"]},
    )
    await Tortoise.generate_schemas()

    set_default_adapter(TortoiseAdapter())

    app = FastAPI()
    router = DefaultRouter()
    router.register("authors", TAuthorViewSet, basename="author")
    router.register("books", TBookViewSet, basename="book")
    router.register("tags", TTagViewSet, basename="tag")
    router.register("reviews", TReviewViewSet, basename="review")
    app.include_router(router.urls, prefix="/api")

    yield app

    reset_default_adapter()
    await Tortoise.close_connections()


@pytest.fixture
def client(tortoise_app):
    return APIClient(tortoise_app)
