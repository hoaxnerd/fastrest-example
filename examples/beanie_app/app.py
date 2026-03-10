"""
Beanie (MongoDB) example — document-based REST API.

Beanie is a MongoDB ODM built on Pydantic. FastREST auto-detects string
primary keys (MongoDB ObjectIds) and adjusts URL routing accordingly.

Run:
    pip install fastrest[beanie] uvicorn
    # Requires a running MongoDB instance (or use mongomock for testing)
    uvicorn examples.beanie_app.app:app --reload

Note: For local development without MongoDB, you can swap the client:
    from mongomock_motor import AsyncMongoMockClient
    client = AsyncMongoMockClient()
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from beanie import Document, init_beanie
from pydantic import Field
from motor.motor_asyncio import AsyncIOMotorClient

from fastrest.routers import DefaultRouter
from fastrest.compat.orm import set_default_adapter
from fastrest.compat.orm.beanie import BeanieAdapter
from fastrest.settings import configure
from fastrest.filters import SearchFilter, OrderingFilter


# ── Models (Pydantic documents) ────────────────────────────────────

class Author(Document):
    name: str
    bio: str | None = None
    is_active: bool = True

    class Settings:
        name = "authors"


class Book(Document):
    title: str = Field(max_length=300)
    price: float
    in_stock: bool = True
    description: str | None = None
    author_id: str | None = None  # string reference to Author ObjectId

    class Settings:
        name = "books"


class Tag(Document):
    name: str = Field(max_length=50)
    slug: str = Field(max_length=50)

    class Settings:
        name = "tags"


# ── Adapter ─────────────────────────────────────────────────────────

set_default_adapter(BeanieAdapter())


# ── Router ──────────────────────────────────────────────────────────

router = DefaultRouter()

# serve() auto-detects string PK type for MongoDB ObjectIds
router.serve(Author)
router.serve(
    Book,
    filter_backends=[SearchFilter, OrderingFilter],
    search_fields=["title", "description"],
    ordering_fields=["title", "price"],
)
router.serve(Tag, readonly=True)


# ── App ─────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app):
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    await init_beanie(
        database=client.beanie_example,
        document_models=[Author, Book, Tag],
    )
    yield
    client.close()


app = FastAPI(title="Beanie (MongoDB) API", lifespan=lifespan)

configure(app, {
    "SKILL_NAME": "beanie-api",
    "SKILL_BASE_URL": "http://localhost:8000/api",
})

app.include_router(router.urls, prefix="/api")
# No session middleware needed — Beanie manages connections internally
