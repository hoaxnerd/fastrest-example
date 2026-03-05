"""Test fixtures for the bookstore example app."""

import pytest
import pytest_asyncio
from fastapi import FastAPI, Request
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from fastrest.routers import DefaultRouter
from fastrest.test import APIClient

from models import Base
from views import AuthorViewSet, BookViewSet, TagViewSet, ReviewViewSet, BookRateThrottle


@pytest_asyncio.fixture
async def db():
    """In-memory SQLite for tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield engine, session_factory
    await engine.dispose()


@pytest.fixture(autouse=True)
def clear_throttle_cache():
    """Clear throttle caches between tests."""
    BookRateThrottle.cache.clear()


@pytest.fixture
def bookstore_app(db):
    """Fully wired FastAPI app for testing."""
    engine, session_factory = db

    app = FastAPI()
    router = DefaultRouter()
    router.register("authors", AuthorViewSet, basename="author")
    router.register("books", BookViewSet, basename="book")
    router.register("tags", TagViewSet, basename="tag")
    router.register("reviews", ReviewViewSet, basename="review")
    app.include_router(router.urls, prefix="/api")

    viewsets = [AuthorViewSet, BookViewSet, TagViewSet, ReviewViewSet]

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


@pytest.fixture
def client(bookstore_app):
    return APIClient(bookstore_app)
