"""
SQLModel example — Pydantic-native models with SQLAlchemy backend.

SQLModel co-installs SQLAlchemy, so you must set the adapter explicitly.
Otherwise the API is identical to the SQLAlchemy example.

Run:
    pip install fastrest[sqlmodel] aiosqlite uvicorn
    uvicorn examples.sqlmodel_app.app:app --reload
"""

from fastapi import FastAPI, Request
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from fastrest.routers import DefaultRouter
from fastrest.compat.orm import set_default_adapter
from fastrest.compat.orm.sqlmodel import SQLModelAdapter
from fastrest.settings import configure
from fastrest.pagination import PageNumberPagination
from fastrest.filters import SearchFilter, OrderingFilter


# ── Models ──────────────────────────────────────────────────────────

class Author(SQLModel, table=True):
    __tablename__ = "authors"
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=200)
    bio: str | None = Field(default=None)
    is_active: bool = Field(default=True)
    books: list["Book"] = Relationship(back_populates="author")


class Book(SQLModel, table=True):
    __tablename__ = "books"
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(max_length=300)
    price: float
    in_stock: bool = Field(default=True)
    description: str | None = Field(default=None)
    author_id: int | None = Field(default=None, foreign_key="authors.id")
    author: Author | None = Relationship(back_populates="books")


class Category(SQLModel, table=True):
    __tablename__ = "categories"
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=100)
    slug: str = Field(max_length=100)


# ── Adapter — must be set explicitly for SQLModel ───────────────────

set_default_adapter(SQLModelAdapter())


# ── Router ──────────────────────────────────────────────────────────

router = DefaultRouter()
router.serve(Author)
router.serve(
    Book,
    filter_backends=[SearchFilter, OrderingFilter],
    search_fields=["title", "description"],
    ordering_fields=["title", "price"],
)
router.serve(Category, readonly=True)


# ── App ─────────────────────────────────────────────────────────────

engine = create_async_engine("sqlite+aiosqlite:///./sqlmodel_example.db")
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

app = FastAPI(title="SQLModel API")

configure(app, {
    "SKILL_NAME": "sqlmodel-api",
    "SKILL_BASE_URL": "http://localhost:8000/api",
})

app.include_router(router.urls, prefix="/api")


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


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
