"""Test the API root and general app behavior."""

import pytest


@pytest.mark.asyncio
async def test_api_root(client):
    """DefaultRouter provides a root listing of all registered endpoints."""
    resp = await client.get("/api/")
    assert resp.status_code == 200
    data = resp.json()
    assert "authors" in data
    assert "books" in data
    assert "tags" in data
    assert "reviews" in data


@pytest.mark.asyncio
async def test_not_found(client):
    resp = await client.get("/api/books/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_full_workflow(client):
    """End-to-end: create author, create book, add review, query everything."""
    # 1. Create author
    author = await client.post("/api/authors", json={
        "name": "Isaac Asimov",
        "bio": "Biochemistry professor and prolific writer.",
    })
    assert author.status_code == 201
    author_id = author.json()["id"]

    # 2. Create book
    book = await client.post("/api/books", json={
        "title": "Foundation",
        "isbn": "0553293354",
        "price": 8.99,
        "author_id": author_id,
    })
    assert book.status_code == 201
    book_id = book.json()["id"]

    # 3. Add reviews
    await client.post("/api/reviews", json={
        "book_id": book_id,
        "reviewer_name": "Reader1",
        "rating": 5,
        "comment": "A timeless classic.",
    })
    await client.post("/api/reviews", json={
        "book_id": book_id,
        "reviewer_name": "Reader2",
        "rating": 4,
    })

    # 4. List author's books
    resp = await client.get(f"/api/authors/{author_id}/books")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["title"] == "Foundation"

    # 5. Verify in-stock filter
    resp = await client.get("/api/books/in-stock")
    assert resp.status_code == 200
    assert any(b["title"] == "Foundation" for b in resp.json())

    # 6. Toggle stock off
    await client.post(f"/api/books/{book_id}/toggle-stock")
    resp = await client.get("/api/books/in-stock")
    assert not any(b["title"] == "Foundation" for b in resp.json())

    # 7. Delete reviews first (FK constraint)
    reviews = await client.get("/api/reviews")
    for r in reviews.json():
        if r["book_id"] == book_id:
            await client.delete(f"/api/reviews/{r['id']}")

    # 8. Delete book
    resp = await client.delete(f"/api/books/{book_id}")
    assert resp.status_code == 204

    # 9. Delete author
    resp = await client.delete(f"/api/authors/{author_id}")
    assert resp.status_code == 204
