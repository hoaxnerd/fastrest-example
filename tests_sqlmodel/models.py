"""Bookstore domain models using SQLModel."""

from sqlmodel import SQLModel, Field, Relationship


class SMAuthor(SQLModel, table=True):
    __tablename__ = "sm_authors"
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=200)
    bio: str | None = Field(default=None)
    is_active: bool = Field(default=True)
    books: list["SMBook"] = Relationship(back_populates="author")


class SMBook(SQLModel, table=True):
    __tablename__ = "sm_books"
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(max_length=300)
    isbn: str | None = Field(default=None, max_length=13)
    price: float
    in_stock: bool = Field(default=True)
    description: str | None = Field(default=None)
    author_id: int = Field(foreign_key="sm_authors.id")
    author: SMAuthor | None = Relationship(back_populates="books")
    reviews: list["SMReview"] = Relationship(back_populates="book")


class SMTag(SQLModel, table=True):
    __tablename__ = "sm_tags"
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=50)
    slug: str = Field(max_length=50)


class SMReview(SQLModel, table=True):
    __tablename__ = "sm_reviews"
    id: int | None = Field(default=None, primary_key=True)
    book_id: int = Field(foreign_key="sm_books.id")
    reviewer_name: str = Field(max_length=100)
    rating: int
    comment: str | None = Field(default=None)
    book: SMBook | None = Relationship(back_populates="reviews")
