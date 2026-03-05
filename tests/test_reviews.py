"""Tests for the Review endpoints."""

import pytest
import pytest_asyncio

AUTH_HEADERS = {"Authorization": "Bearer admin-token-001"}


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
async def test_create_review_authenticated(client, book_id):
    resp = await client.post("/api/reviews", json={
        "book_id": book_id,
        "reviewer_name": "Alice",
        "rating": 5,
        "comment": "Masterpiece!",
    }, headers=AUTH_HEADERS)
    assert resp.status_code == 201
    data = resp.json()
    assert data["rating"] == 5
    assert data["reviewer_name"] == "Alice"


@pytest.mark.asyncio
async def test_create_review_unauthenticated_returns_401(client, book_id):
    resp = await client.post("/api/reviews", json={
        "book_id": book_id,
        "reviewer_name": "Bob",
        "rating": 4,
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_reviews_without_auth(client, book_id):
    """GET is allowed without auth (IsAuthenticatedOrReadOnly)."""
    await client.post("/api/reviews", json={
        "book_id": book_id, "reviewer_name": "R1", "rating": 3,
    }, headers=AUTH_HEADERS)

    resp = await client.get("/api/reviews")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_review_rating_validation(client, book_id):
    """Rating must be 1-5 — enforced by validate_rating hook."""
    resp = await client.post("/api/reviews", json={
        "book_id": book_id,
        "reviewer_name": "Bob",
        "rating": 0,
    }, headers=AUTH_HEADERS)
    assert resp.status_code == 400

    resp = await client.post("/api/reviews", json={
        "book_id": book_id,
        "reviewer_name": "Bob",
        "rating": 6,
    }, headers=AUTH_HEADERS)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_review_rating_valid_boundaries(client, book_id):
    """1 and 5 should both be accepted."""
    resp = await client.post("/api/reviews", json={
        "book_id": book_id, "reviewer_name": "Min", "rating": 1,
    }, headers=AUTH_HEADERS)
    assert resp.status_code == 201

    resp = await client.post("/api/reviews", json={
        "book_id": book_id, "reviewer_name": "Max", "rating": 5,
    }, headers=AUTH_HEADERS)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_review_missing_required_fields(client, book_id):
    """reviewer_name and rating are required."""
    resp = await client.post("/api/reviews", json={
        "book_id": book_id,
    }, headers=AUTH_HEADERS)
    assert resp.status_code == 422
