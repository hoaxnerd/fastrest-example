"""Tests for the Tag endpoints."""

import pytest


@pytest.mark.asyncio
async def test_create_tag(client):
    resp = await client.post("/api/tags", json={
        "name": "Science Fiction",
        "slug": "sci-fi",
    })
    assert resp.status_code == 201
    assert resp.json()["slug"] == "sci-fi"


@pytest.mark.asyncio
async def test_list_tags(client):
    await client.post("/api/tags", json={"name": "Fantasy", "slug": "fantasy"})
    await client.post("/api/tags", json={"name": "Horror", "slug": "horror"})

    resp = await client.get("/api/tags")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_update_tag(client):
    create = await client.post("/api/tags", json={"name": "Scifi", "slug": "scifi"})
    tag_id = create.json()["id"]

    resp = await client.put(f"/api/tags/{tag_id}", json={
        "name": "Science Fiction",
        "slug": "sci-fi",
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "Science Fiction"


@pytest.mark.asyncio
async def test_delete_tag(client):
    create = await client.post("/api/tags", json={"name": "Temp", "slug": "temp"})
    tag_id = create.json()["id"]

    resp = await client.delete(f"/api/tags/{tag_id}")
    assert resp.status_code == 204
