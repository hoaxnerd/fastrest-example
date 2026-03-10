"""Pagination, search, and ordering tests for SQLModel bookstore."""

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def seeded_books(client):
    """Create an author and 12 books for pagination testing."""
    resp = await client.post("/api/authors", json={"name": "Author"})
    author_id = resp.json()["id"]
    for i in range(12):
        await client.post("/api/books", json={
            "title": f"Book {i:02d}",
            "price": 10.0 + i,
            "description": f"Description for book {i:02d}",
            "author_id": author_id,
        })
    return author_id


@pytest.mark.asyncio
async def test_default_pagination(client, seeded_books):
    resp = await client.get("/api/books")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert "count" in data
    assert data["count"] == 12
    # page_size is 5
    assert len(data["results"]) == 5


@pytest.mark.asyncio
async def test_page_2(client, seeded_books):
    resp = await client.get("/api/books?page=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 5


@pytest.mark.asyncio
async def test_page_3(client, seeded_books):
    resp = await client.get("/api/books?page=3")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 2  # 12 - 5 - 5 = 2


@pytest.mark.asyncio
async def test_custom_page_size(client, seeded_books):
    resp = await client.get("/api/books?page_size=3")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 3


@pytest.mark.asyncio
async def test_search(client, seeded_books):
    resp = await client.get("/api/books?search=Book 01")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["results"][0]["title"] == "Book 01"


@pytest.mark.asyncio
async def test_ordering_by_price_asc(client, seeded_books):
    resp = await client.get("/api/books?ordering=price&page_size=12")
    assert resp.status_code == 200
    prices = [b["price"] for b in resp.json()["results"]]
    assert prices == sorted(prices)


@pytest.mark.asyncio
async def test_ordering_by_price_desc(client, seeded_books):
    resp = await client.get("/api/books?ordering=-price&page_size=12")
    assert resp.status_code == 200
    prices = [b["price"] for b in resp.json()["results"]]
    assert prices == sorted(prices, reverse=True)
