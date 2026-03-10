"""Bookstore domain models using Beanie (MongoDB)."""

from beanie import Document
from pydantic import Field


class BAuthor(Document):
    name: str
    bio: str | None = None
    is_active: bool = True

    class Settings:
        name = "b_authors"


class BTag(Document):
    name: str = Field(max_length=50)
    slug: str = Field(max_length=50)

    class Settings:
        name = "b_tags"


class BBook(Document):
    title: str = Field(max_length=300)
    isbn: str | None = None
    price: float
    in_stock: bool = True
    description: str | None = None
    author_id: str  # String reference to BAuthor id

    class Settings:
        name = "b_books"


class BReview(Document):
    book_id: str  # String reference to BBook id
    reviewer_name: str = Field(max_length=100)
    rating: int
    comment: str | None = None

    class Settings:
        name = "b_reviews"
