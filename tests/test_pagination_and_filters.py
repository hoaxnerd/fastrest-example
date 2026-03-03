"""Tests for pagination and filtering on the bookstore API."""

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def author_id(client):
    resp = await client.post("/api/authors", json={"name": "Pagination Author"})
    return resp.json()["id"]


@pytest_asyncio.fixture
async def seeded_books(client, author_id):
    """Create 25 books for pagination testing."""
    for i in range(1, 26):
        await client.post("/api/books", json={
            "title": f"Book {i:02d}",
            "isbn": f"{1000000000 + i}",
            "price": float(i),
            "author_id": author_id,
        })
    return author_id


@pytest.mark.asyncio
async def test_books_are_paginated(client, seeded_books):
    resp = await client.get("/api/books")
    data = resp.json()
    assert "count" in data
    assert "results" in data
    assert data["count"] == 25
    assert len(data["results"]) == 20  # BookPagination.page_size = 20


@pytest.mark.asyncio
async def test_books_second_page(client, seeded_books):
    resp = await client.get("/api/books?page=2")
    data = resp.json()
    assert len(data["results"]) == 5  # 25 - 20 = 5


@pytest.mark.asyncio
async def test_books_custom_page_size(client, seeded_books):
    resp = await client.get("/api/books?page_size=10")
    data = resp.json()
    assert len(data["results"]) == 10


@pytest.mark.asyncio
async def test_books_search_by_title(client, seeded_books):
    resp = await client.get("/api/books?search=Book 01")
    data = resp.json()
    assert data["count"] == 1
    assert data["results"][0]["title"] == "Book 01"


@pytest.mark.asyncio
async def test_books_search_no_match(client, seeded_books):
    resp = await client.get("/api/books?search=nonexistent")
    data = resp.json()
    assert data["count"] == 0


@pytest.mark.asyncio
async def test_books_ordering_by_price_desc(client, seeded_books):
    resp = await client.get("/api/books?ordering=-price&page_size=5")
    data = resp.json()
    prices = [b["price"] for b in data["results"]]
    assert prices == sorted(prices, reverse=True)


@pytest.mark.asyncio
async def test_books_ordering_by_title(client, seeded_books):
    resp = await client.get("/api/books?ordering=title&page_size=5")
    data = resp.json()
    titles = [b["title"] for b in data["results"]]
    assert titles == sorted(titles)


@pytest.mark.asyncio
async def test_books_search_and_ordering(client, seeded_books):
    resp = await client.get("/api/books?search=Book&ordering=-price&page_size=3")
    data = resp.json()
    assert data["count"] == 25
    prices = [b["price"] for b in data["results"]]
    assert prices == sorted(prices, reverse=True)
    assert len(data["results"]) == 3


@pytest.mark.asyncio
async def test_openapi_shows_query_params(client):
    """Pagination and filter query params should appear in OpenAPI schema."""
    resp = await client.get("/openapi.json")
    paths = resp.json()["paths"]
    book_list = paths.get("/api/books", {}).get("get", {})
    param_names = [p["name"] for p in book_list.get("parameters", [])]
    assert "page" in param_names
    assert "page_size" in param_names
    assert "search" in param_names
    assert "ordering" in param_names
