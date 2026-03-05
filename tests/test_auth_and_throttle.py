"""Tests for authentication and throttling features from a consumer perspective."""

import pytest
import pytest_asyncio


AUTH_HEADERS = {"Authorization": "Bearer admin-token-001"}
USER_HEADERS = {"Authorization": "Bearer user-token-002"}


# --- Authentication ---

class TestReviewAuthentication:
    """ReviewViewSet requires authentication for write operations."""

    @pytest_asyncio.fixture(autouse=True)
    async def _setup(self, client):
        """Create an author + book for reviews."""
        author = await client.post("/api/authors", json={"name": "Auth Test Author"})
        book = await client.post("/api/books", json={
            "title": "Auth Book",
            "price": 10.0,
            "author_id": author.json()["id"],
        })
        self.book_id = book.json()["id"]
        self.client = client

    @pytest.mark.asyncio
    async def test_get_reviews_without_auth(self):
        """GET is allowed without auth (IsAuthenticatedOrReadOnly)."""
        resp = await self.client.get("/api/reviews")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_post_review_without_auth_returns_401(self):
        """POST requires authentication."""
        resp = await self.client.post("/api/reviews", json={
            "book_id": self.book_id,
            "reviewer_name": "Anon",
            "rating": 3,
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_post_review_with_invalid_token_returns_401(self):
        resp = await self.client.post("/api/reviews", json={
            "book_id": self.book_id,
            "reviewer_name": "Anon",
            "rating": 3,
        }, headers={"Authorization": "Bearer bad-token"})
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_post_review_with_valid_token(self):
        resp = await self.client.post("/api/reviews", json={
            "book_id": self.book_id,
            "reviewer_name": "AuthUser",
            "rating": 4,
            "comment": "Great!",
        }, headers=AUTH_HEADERS)
        assert resp.status_code == 201
        assert resp.json()["reviewer_name"] == "AuthUser"

    @pytest.mark.asyncio
    async def test_different_users_can_create(self):
        """Both admin and regular user tokens work."""
        resp1 = await self.client.post("/api/reviews", json={
            "book_id": self.book_id, "reviewer_name": "Admin", "rating": 5,
        }, headers=AUTH_HEADERS)
        assert resp1.status_code == 201

        resp2 = await self.client.post("/api/reviews", json={
            "book_id": self.book_id, "reviewer_name": "Reader", "rating": 4,
        }, headers=USER_HEADERS)
        assert resp2.status_code == 201


class TestNoAuthEndpoints:
    """AuthorViewSet and TagViewSet have no auth — still fully open."""

    @pytest.mark.asyncio
    async def test_create_author_without_auth(self, client):
        resp = await client.post("/api/authors", json={"name": "Open Author"})
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_create_tag_without_auth(self, client):
        resp = await client.post("/api/tags", json={"name": "open", "slug": "open"})
        assert resp.status_code == 201


# --- Throttling ---

class TestBookThrottling:
    """BookViewSet has a 100/min throttle — hard to hit in tests,
    but we verify the viewset accepts requests normally with throttle configured."""

    @pytest.mark.asyncio
    async def test_books_endpoint_works_with_throttle(self, client):
        author = await client.post("/api/authors", json={"name": "Throttle Author"})
        aid = author.json()["id"]

        resp = await client.post("/api/books", json={
            "title": "Throttled Book", "price": 5.0, "author_id": aid,
        })
        assert resp.status_code == 201

        resp = await client.get("/api/books")
        assert resp.status_code == 200
