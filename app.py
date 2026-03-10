"""Main FastAPI application — the entry point a developer writes."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from fastrest.routers import DefaultRouter
from fastrest.settings import configure
from fastrest.mcp import mount_mcp

from db import SessionLocal, init_db
from views import AuthorViewSet, BookViewSet, TagViewSet, ReviewViewSet


# --- Router setup (DRF-style) ---
router = DefaultRouter()
router.register("authors", AuthorViewSet, basename="author")
router.register("books", BookViewSet, basename="book")
router.register("tags", TagViewSet, basename="tag")
router.register("reviews", ReviewViewSet, basename="review")


# --- FastAPI app ---
@asynccontextmanager
async def lifespan(app):
    await init_db()
    yield


app = FastAPI(title="Bookstore API", version="0.2.0", lifespan=lifespan)


# --- App configuration (Django-style settings) ---
configure(app, {
    # Agent integration
    "SKILL_NAME": "bookstore",
    "SKILL_BASE_URL": "http://localhost:8000/api",
    "SKILL_DESCRIPTION": "Manage a bookstore with authors, books, tags, and reviews.",
    "SKILL_AUTH_DESCRIPTION": "Use Bearer token in the Authorization header. Demo tokens: admin-token-001 (admin), user-token-002 (reader).",
    "SKILL_INCLUDE_EXAMPLES": True,
    "SKILL_MAX_EXAMPLES_PER_RESOURCE": 3,

    # MCP server
    "MCP_ENABLED": True,
    "MCP_PREFIX": "/mcp",
})

app.include_router(router.urls, prefix="/api")

# --- Mount MCP server for agent integration ---
mount_mcp(app, router)


@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    """Inject a DB session into every viewset instance."""
    async with SessionLocal() as session:
        async with session.begin():
            # Patch all viewset classes to use this session
            viewsets = [AuthorViewSet, BookViewSet, TagViewSet, ReviewViewSet]
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
