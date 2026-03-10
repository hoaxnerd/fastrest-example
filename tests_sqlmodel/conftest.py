"""Test fixtures for the SQLModel bookstore example."""

import pytest
import pytest_asyncio
from fastapi import FastAPI, Request
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from fastrest.routers import DefaultRouter
from fastrest.compat.orm import set_default_adapter, reset_default_adapter
from fastrest.compat.orm.sqlmodel import SQLModelAdapter
from fastrest.test import APIClient

from tests_sqlmodel.models import SMAuthor, SMBook, SMTag, SMReview
from tests_sqlmodel.views import (
    SMAuthorViewSet, SMBookViewSet, SMTagViewSet, SMReviewViewSet,
)


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield engine, session_factory
    await engine.dispose()


@pytest.fixture
def sqlmodel_app(db):
    engine, session_factory = db

    set_default_adapter(SQLModelAdapter())

    app = FastAPI()
    router = DefaultRouter()
    router.register("authors", SMAuthorViewSet, basename="author")
    router.register("books", SMBookViewSet, basename="book")
    router.register("tags", SMTagViewSet, basename="tag")
    router.register("reviews", SMReviewViewSet, basename="review")
    app.include_router(router.urls, prefix="/api")

    viewsets = [SMAuthorViewSet, SMBookViewSet, SMTagViewSet, SMReviewViewSet]

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

    yield app
    reset_default_adapter()


@pytest.fixture
def client(sqlmodel_app):
    return APIClient(sqlmodel_app)
