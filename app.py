"""Main FastAPI application — the entry point a developer writes."""

from fastapi import FastAPI, Request

from fastrest.routers import DefaultRouter

from db import SessionLocal, init_db
from views import AuthorViewSet, BookViewSet, TagViewSet, ReviewViewSet

# --- Router setup (DRF-style) ---
router = DefaultRouter()
router.register("authors", AuthorViewSet, basename="author")
router.register("books", BookViewSet, basename="book")
router.register("tags", TagViewSet, basename="tag")
router.register("reviews", ReviewViewSet, basename="review")

# --- FastAPI app ---
app = FastAPI(title="Bookstore API", version="0.1.0")
app.include_router(router.urls, prefix="/api")


@app.on_event("startup")
async def startup():
    await init_db()


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
