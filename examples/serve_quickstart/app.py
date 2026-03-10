"""
Zero-config REST API with router.serve() — the simplest way to use FastREST.

This example shows how to go from SQLAlchemy models to a full REST API
with search, pagination, filtering, auth, throttling, and agent integration
in under 30 lines of application code.

Run:
    pip install fastrest[sqlalchemy,mcp] aiosqlite uvicorn
    uvicorn examples.serve_quickstart.app:app --reload

Endpoints:
    GET  /docs                  → Swagger UI
    GET  /api/                  → API root
    GET  /api/authors           → List, search, paginate
    POST /api/authors           → Create
    GET  /api/authors/{pk}      → Retrieve
    PUT  /api/authors/{pk}      → Update
    PATCH /api/authors/{pk}     → Partial update
    DELETE /api/authors/{pk}    → Delete
    GET  /api/books             → Paginated, searchable, orderable
    GET  /api/categories        → Read-only
    GET  /api/SKILL.md          → Agent-readable API documentation
    GET  /api/manifest.json     → Structured API metadata
"""

from fastapi import FastAPI, Request
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from fastrest.routers import DefaultRouter
from fastrest.settings import configure
from fastrest.mcp import mount_mcp
from fastrest.pagination import PageNumberPagination
from fastrest.filters import SearchFilter, OrderingFilter
from fastrest.permissions import IsAuthenticatedOrReadOnly


# ── Models ──────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass

class Author(Base):
    __tablename__ = "authors"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    bio = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)

class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300), nullable=False)
    price = Column(Float, nullable=False)
    in_stock = Column(Boolean, default=True)
    description = Column(Text, nullable=True)
    author_id = Column(Integer, ForeignKey("authors.id"), nullable=True)

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    slug = Column(String(100), nullable=False)


# ── Router — one line per model ─────────────────────────────────────

router = DefaultRouter()

# Full CRUD, all fields, auto-pluralized prefix
router.serve(Author)

# With pagination, search, and ordering
class BookPagination(PageNumberPagination):
    page_size = 10
    max_page_size = 50

BookViewSet = router.serve(
    Book,
    pagination_class=BookPagination,
    filter_backends=[SearchFilter, OrderingFilter],
    search_fields=["title", "description"],
    ordering_fields=["title", "price"],
    ordering=["title"],
)
BookViewSet.skill_description = "Search and browse the book catalog."

# Read-only — GET endpoints only, no POST/PUT/DELETE
router.serve(Category, readonly=True)


# ── App ─────────────────────────────────────────────────────────────

engine = create_async_engine("sqlite+aiosqlite:///./quickstart.db")
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

app = FastAPI(title="Quickstart API")

configure(app, {
    "SKILL_NAME": "quickstart-api",
    "SKILL_BASE_URL": "http://localhost:8000/api",
    "SKILL_DESCRIPTION": "A minimal bookstore API built with router.serve().",
    "MCP_PREFIX": "/mcp",
})

app.include_router(router.urls, prefix="/api")
mount_mcp(app, router)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Session injection — the only boilerplate needed for SQLAlchemy
_viewsets = [vs for _, vs, _ in router.registry]

@app.middleware("http")
async def db_session(request: Request, call_next):
    async with SessionLocal() as session:
        async with session.begin():
            originals = {}
            for vs in _viewsets:
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
                for vs in _viewsets:
                    vs.__init__ = originals[vs]
            return response
