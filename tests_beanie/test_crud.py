"""CRUD tests for Beanie (MongoDB) bookstore."""

import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def author_id(client):
    resp = await client.post("/api/authors", json={"name": "Jane Austen", "bio": "English novelist"})
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest_asyncio.fixture
async def book_id(client, author_id):
    resp = await client.post("/api/books", json={
        "title": "Pride and Prejudice",
        "isbn": "9780141439518",
        "price": 12.99,
        "author_id": str(author_id),
    })
    assert resp.status_code == 201
    return resp.json()["id"]


# ── Author CRUD ──

@pytest.mark.asyncio
async def test_create_author(client):
    resp = await client.post("/api/authors", json={"name": "New Author"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "New Author"
    assert data["id"] is not None
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_list_authors(client, author_id):
    resp = await client.get("/api/authors")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_retrieve_author(client, author_id):
    resp = await client.get(f"/api/authors/{author_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Jane Austen"


@pytest.mark.asyncio
async def test_update_author(client, author_id):
    resp = await client.put(f"/api/authors/{author_id}", json={
        "name": "Jane Austen Updated", "bio": "Updated bio", "is_active": False
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Jane Austen Updated"


@pytest.mark.asyncio
async def test_partial_update_author(client, author_id):
    resp = await client.patch(f"/api/authors/{author_id}", json={"bio": "Partial update"})
    assert resp.status_code == 200
    assert resp.json()["bio"] == "Partial update"


@pytest.mark.asyncio
async def test_delete_author(client, author_id):
    resp = await client.delete(f"/api/authors/{author_id}")
    assert resp.status_code == 204
    resp = await client.get(f"/api/authors/{author_id}")
    assert resp.status_code == 404


# ── Book CRUD ──

@pytest.mark.asyncio
async def test_create_book(client, author_id):
    resp = await client.post("/api/books", json={
        "title": "New Book", "price": 15.99, "author_id": str(author_id)
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "New Book"
    assert data["in_stock"] is True


@pytest.mark.asyncio
async def test_retrieve_book(client, book_id):
    resp = await client.get(f"/api/books/{book_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Pride and Prejudice"


@pytest.mark.asyncio
async def test_update_book(client, book_id, author_id):
    resp = await client.put(f"/api/books/{book_id}", json={
        "title": "Updated Title", "price": 19.99, "author_id": str(author_id)
    })
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_delete_book(client, book_id):
    resp = await client.delete(f"/api/books/{book_id}")
    assert resp.status_code == 204


# ── Tag CRUD ──

@pytest.mark.asyncio
async def test_create_tag(client):
    resp = await client.post("/api/tags", json={"name": "Fiction", "slug": "fiction"})
    assert resp.status_code == 201
    assert resp.json()["name"] == "Fiction"


@pytest.mark.asyncio
async def test_list_tags(client):
    await client.post("/api/tags", json={"name": "Sci-fi", "slug": "sci-fi"})
    resp = await client.get("/api/tags")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


# ── Review CRUD ──

@pytest.mark.asyncio
async def test_create_review(client, book_id):
    resp = await client.post("/api/reviews", json={
        "book_id": str(book_id), "reviewer_name": "Bob", "rating": 5, "comment": "Great!"
    })
    assert resp.status_code == 201
    assert resp.json()["rating"] == 5


@pytest.mark.asyncio
async def test_review_validation(client, book_id):
    resp = await client.post("/api/reviews", json={
        "book_id": str(book_id), "reviewer_name": "Bob", "rating": 6
    })
    assert resp.status_code == 400


# ── Custom Actions ──

@pytest.mark.asyncio
async def test_author_books_action(client, book_id, author_id):
    resp = await client.get(f"/api/authors/{author_id}/books")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["author_id"] == str(author_id)


@pytest.mark.asyncio
async def test_book_in_stock_action(client, book_id):
    resp = await client.get("/api/books/in-stock")
    assert resp.status_code == 200
    assert all(b["in_stock"] for b in resp.json())


@pytest.mark.asyncio
async def test_book_toggle_stock(client, book_id):
    resp = await client.post(f"/api/books/{book_id}/toggle-stock")
    assert resp.status_code == 200
    assert resp.json()["in_stock"] is False

    resp = await client.post(f"/api/books/{book_id}/toggle-stock")
    assert resp.status_code == 200
    assert resp.json()["in_stock"] is True
