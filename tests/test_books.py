"""Tests for the Book endpoints."""

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def author_id(client):
    """Create an author and return their ID — needed for every book."""
    resp = await client.post("/api/authors", json={"name": "Test Author"})
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_book(client, author_id):
    resp = await client.post("/api/books", json={
        "title": "The Left Hand of Darkness",
        "isbn": "9780441478125",
        "price": 12.99,
        "author_id": author_id,
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "The Left Hand of Darkness"
    assert data["in_stock"] is True  # default


@pytest.mark.asyncio
async def test_create_book_missing_required(client, author_id):
    """Price and title are required."""
    resp = await client.post("/api/books", json={
        "author_id": author_id,
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_book_negative_price(client, author_id):
    """Our custom FloatField(min_value=0.01) should reject this."""
    resp = await client.post("/api/books", json={
        "title": "Free Book",
        "price": -5.00,
        "author_id": author_id,
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_isbn_validation(client, author_id):
    """ISBN must be 10 or 13 chars if provided."""
    resp = await client.post("/api/books", json={
        "title": "Bad ISBN Book",
        "isbn": "12345",
        "price": 10.00,
        "author_id": author_id,
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_books(client, author_id):
    await client.post("/api/books", json={
        "title": "Book A", "price": 10.0, "author_id": author_id,
    })
    await client.post("/api/books", json={
        "title": "Book B", "price": 20.0, "author_id": author_id,
    })

    resp = await client.get("/api/books")
    assert resp.status_code == 200
    data = resp.json()
    # BookViewSet has pagination, so response is an envelope
    assert data["count"] >= 2
    assert len(data["results"]) >= 2


@pytest.mark.asyncio
async def test_toggle_stock_action(client, author_id):
    """Test custom @action that toggles in_stock."""
    create = await client.post("/api/books", json={
        "title": "Toggle Me", "price": 5.0, "author_id": author_id,
    })
    book_id = create.json()["id"]
    assert create.json()["in_stock"] is True

    # Toggle off
    resp = await client.post(f"/api/books/{book_id}/toggle-stock")
    assert resp.status_code == 200
    assert resp.json()["in_stock"] is False

    # Toggle back on
    resp = await client.post(f"/api/books/{book_id}/toggle-stock")
    assert resp.status_code == 200
    assert resp.json()["in_stock"] is True


@pytest.mark.asyncio
async def test_in_stock_action(client, author_id):
    """Test custom @action that lists only in-stock books."""
    await client.post("/api/books", json={
        "title": "Available", "price": 10.0, "author_id": author_id,
    })
    out_of_stock = await client.post("/api/books", json={
        "title": "Unavailable", "price": 10.0, "author_id": author_id,
    })
    # Toggle the second one out of stock
    book_id = out_of_stock.json()["id"]
    await client.post(f"/api/books/{book_id}/toggle-stock")

    resp = await client.get("/api/books/in-stock")
    assert resp.status_code == 200
    titles = [b["title"] for b in resp.json()]
    assert "Available" in titles
    assert "Unavailable" not in titles


@pytest.mark.asyncio
async def test_update_book(client, author_id):
    create = await client.post("/api/books", json={
        "title": "Old Title", "price": 10.0, "author_id": author_id,
    })
    book_id = create.json()["id"]

    resp = await client.put(f"/api/books/{book_id}", json={
        "title": "New Title", "price": 12.0, "author_id": author_id,
    })
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"
    assert resp.json()["price"] == 12.0


@pytest.mark.asyncio
async def test_delete_book(client, author_id):
    create = await client.post("/api/books", json={
        "title": "Doomed", "price": 1.0, "author_id": author_id,
    })
    book_id = create.json()["id"]

    resp = await client.delete(f"/api/books/{book_id}")
    assert resp.status_code == 204

    resp = await client.get(f"/api/books/{book_id}")
    assert resp.status_code == 404
