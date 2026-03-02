"""Tests for the Author endpoints — written like a developer would."""

import pytest


@pytest.mark.asyncio
async def test_create_author(client):
    resp = await client.post("/api/authors", json={
        "name": "Ursula K. Le Guin",
        "bio": "American author of novels, children's books, and short stories.",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Ursula K. Le Guin"
    assert data["is_active"] is True  # default
    assert "id" in data


@pytest.mark.asyncio
async def test_list_authors(client):
    await client.post("/api/authors", json={"name": "Author A"})
    await client.post("/api/authors", json={"name": "Author B"})

    resp = await client.get("/api/authors")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_retrieve_author(client):
    create = await client.post("/api/authors", json={"name": "Octavia Butler"})
    author_id = create.json()["id"]

    resp = await client.get(f"/api/authors/{author_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Octavia Butler"


@pytest.mark.asyncio
async def test_update_author(client):
    create = await client.post("/api/authors", json={"name": "Typo Name"})
    author_id = create.json()["id"]

    resp = await client.put(f"/api/authors/{author_id}", json={
        "name": "Corrected Name",
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Corrected Name"


@pytest.mark.asyncio
async def test_partial_update_author(client):
    create = await client.post("/api/authors", json={"name": "N.K. Jemisin"})
    author_id = create.json()["id"]

    resp = await client.patch(f"/api/authors/{author_id}", json={
        "bio": "Three-time Hugo Award winner.",
    })
    assert resp.status_code == 200
    assert resp.json()["bio"] == "Three-time Hugo Award winner."
    assert resp.json()["name"] == "N.K. Jemisin"  # unchanged


@pytest.mark.asyncio
async def test_delete_author(client):
    create = await client.post("/api/authors", json={"name": "To Delete"})
    author_id = create.json()["id"]

    resp = await client.delete(f"/api/authors/{author_id}")
    assert resp.status_code == 204

    # Verify gone
    resp = await client.get(f"/api/authors/{author_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_author_books_action(client):
    """Test the custom @action that lists an author's books."""
    author = await client.post("/api/authors", json={"name": "Frank Herbert"})
    author_id = author.json()["id"]

    # Create some books for this author
    await client.post("/api/books", json={
        "title": "Dune", "price": 15.99, "author_id": author_id,
    })
    await client.post("/api/books", json={
        "title": "Dune Messiah", "price": 14.99, "author_id": author_id,
    })

    resp = await client.get(f"/api/authors/{author_id}/books")
    assert resp.status_code == 200
    books = resp.json()
    assert len(books) == 2
    titles = {b["title"] for b in books}
    assert "Dune" in titles
    assert "Dune Messiah" in titles
