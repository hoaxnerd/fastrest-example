"""Test fixtures for the Beanie (MongoDB) bookstore example."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from beanie import init_beanie
from mongomock_motor import AsyncMongoMockClient

from fastrest.routers import DefaultRouter
from fastrest.compat.orm import set_default_adapter, reset_default_adapter
from fastrest.compat.orm.beanie import BeanieAdapter
from fastrest.test import APIClient

from tests_beanie.models import BAuthor, BBook, BTag, BReview
from tests_beanie.views import (
    BAuthorViewSet, BBookViewSet, BTagViewSet, BReviewViewSet,
)


@pytest_asyncio.fixture
async def beanie_app():
    """Fully wired FastAPI app with Beanie — no session middleware needed."""
    client = AsyncMongoMockClient()
    await init_beanie(
        database=client.testdb,
        document_models=[BAuthor, BBook, BTag, BReview],
    )

    set_default_adapter(BeanieAdapter())

    app = FastAPI()
    router = DefaultRouter()
    router.register("authors", BAuthorViewSet, basename="author")
    router.register("books", BBookViewSet, basename="book")
    router.register("tags", BTagViewSet, basename="tag")
    router.register("reviews", BReviewViewSet, basename="review")
    app.include_router(router.urls, prefix="/api")

    yield app

    # Clean up collections
    for model in [BAuthor, BBook, BTag, BReview]:
        await model.delete_all()
    reset_default_adapter()


@pytest.fixture
def client(beanie_app):
    return APIClient(beanie_app)
