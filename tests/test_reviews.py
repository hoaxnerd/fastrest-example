"""Tests for the Review endpoints."""

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def book_id(client):
    """Create an author + book and return the book ID."""
    author = await client.post("/api/authors", json={"name": "Review Author"})
    book = await client.post("/api/books", json={
        "title": "Reviewed Book",
        "price": 25.0,
        "author_id": author.json()["id"],
    })
    return book.json()["id"]


@pytest.mark.asyncio
async def test_create_review(client, book_id):
    resp = await client.post("/api/reviews", json={
        "book_id": book_id,
        "reviewer_name": "Alice",
        "rating": 5,
        "comment": "Masterpiece!",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["rating"] == 5
    assert data["reviewer_name"] == "Alice"


@pytest.mark.asyncio
async def test_review_rating_validation(client, book_id):
    """Rating must be 1-5 — enforced by validate_rating hook."""
    resp = await client.post("/api/reviews", json={
        "book_id": book_id,
        "reviewer_name": "Bob",
        "rating": 0,
    })
    assert resp.status_code == 400

    resp = await client.post("/api/reviews", json={
        "book_id": book_id,
        "reviewer_name": "Bob",
        "rating": 6,
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_review_rating_valid_boundaries(client, book_id):
    """1 and 5 should both be accepted."""
    resp = await client.post("/api/reviews", json={
        "book_id": book_id, "reviewer_name": "Min", "rating": 1,
    })
    assert resp.status_code == 201

    resp = await client.post("/api/reviews", json={
        "book_id": book_id, "reviewer_name": "Max", "rating": 5,
    })
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_list_reviews(client, book_id):
    await client.post("/api/reviews", json={
        "book_id": book_id, "reviewer_name": "R1", "rating": 3,
    })
    await client.post("/api/reviews", json={
        "book_id": book_id, "reviewer_name": "R2", "rating": 4,
    })

    resp = await client.get("/api/reviews")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_review_missing_required_fields(client, book_id):
    """reviewer_name and rating are required."""
    resp = await client.post("/api/reviews", json={
        "book_id": book_id,
    })
    assert resp.status_code == 422
