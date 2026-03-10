"""
Tortoise ORM example — session-less REST API.

Tortoise manages its own connections, so there's no session middleware.
This is the cleanest setup of all supported ORMs.

Run:
    pip install fastrest[tortoise] aiosqlite uvicorn
    uvicorn examples.tortoise_app.app:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from tortoise import Tortoise, fields
from tortoise.models import Model

from fastrest.routers import DefaultRouter
from fastrest.compat.orm import set_default_adapter
from fastrest.compat.orm.tortoise import TortoiseAdapter
from fastrest.settings import configure
from fastrest.pagination import PageNumberPagination
from fastrest.filters import SearchFilter, OrderingFilter


# ── Models ──────────────────────────────────────────────────────────

class Author(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=200)
    bio = fields.TextField(null=True)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "authors"


class Book(Model):
    id = fields.IntField(primary_key=True)
    title = fields.CharField(max_length=300)
    price = fields.FloatField()
    in_stock = fields.BooleanField(default=True)
    description = fields.TextField(null=True)
    author = fields.ForeignKeyField("models.Author", related_name="books", null=True)

    class Meta:
        table = "books"


class Category(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=100)
    slug = fields.CharField(max_length=100)

    class Meta:
        table = "categories"


# ── Adapter ─────────────────────────────────────────────────────────

set_default_adapter(TortoiseAdapter())


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

@asynccontextmanager
async def lifespan(app):
    await Tortoise.init(
        db_url="sqlite://tortoise_example.db",
        modules={"models": ["examples.tortoise_app.app"]},
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


app = FastAPI(title="Tortoise ORM API", lifespan=lifespan)

configure(app, {
    "SKILL_NAME": "tortoise-api",
    "SKILL_BASE_URL": "http://localhost:8000/api",
})

app.include_router(router.urls, prefix="/api")
# No session middleware needed — Tortoise manages connections internally
