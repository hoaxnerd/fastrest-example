"""Tests for agent integration features: SKILL.md, manifest, MCP, configure."""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport


@pytest_asyncio.fixture
async def client():
    from app import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestSkillEndpoint:
    @pytest.mark.asyncio
    async def test_skill_md_root(self, client):
        resp = await client.get("/api/SKILL.md")
        assert resp.status_code == 200
        assert "text/markdown" in resp.headers["content-type"]
        # Should contain registered resources
        assert "Books" in resp.text
        assert "Authors" in resp.text
        assert "Tags" in resp.text
        assert "Reviews" in resp.text

    @pytest.mark.asyncio
    async def test_skill_md_frontmatter(self, client):
        resp = await client.get("/api/SKILL.md")
        assert "name: bookstore" in resp.text
        assert "description:" in resp.text

    @pytest.mark.asyncio
    async def test_skill_md_per_resource(self, client):
        resp = await client.get("/api/books/SKILL.md")
        assert resp.status_code == 200
        assert "Books" in resp.text
        assert "Authors" not in resp.text

    @pytest.mark.asyncio
    async def test_skill_md_has_fields(self, client):
        resp = await client.get("/api/books/SKILL.md")
        assert "| title |" in resp.text
        assert "| price |" in resp.text

    @pytest.mark.asyncio
    async def test_skill_md_has_endpoints(self, client):
        resp = await client.get("/api/books/SKILL.md")
        text = resp.text
        assert "GET" in text
        assert "POST" in text

    @pytest.mark.asyncio
    async def test_skill_md_has_filters(self, client):
        resp = await client.get("/api/books/SKILL.md")
        assert "search" in resp.text
        assert "ordering" in resp.text

    @pytest.mark.asyncio
    async def test_skill_md_has_custom_description(self, client):
        resp = await client.get("/api/books/SKILL.md")
        assert "Manage the book catalog" in resp.text

    @pytest.mark.asyncio
    async def test_skill_md_has_custom_actions(self, client):
        resp = await client.get("/api/books/SKILL.md")
        assert "in-stock" in resp.text or "in_stock" in resp.text

    @pytest.mark.asyncio
    async def test_skill_not_in_openapi(self, client):
        resp = await client.get("/openapi.json")
        paths = list(resp.json().get("paths", {}).keys())
        skill_paths = [p for p in paths if "SKILL" in p]
        assert skill_paths == []


class TestManifestEndpoint:
    @pytest.mark.asyncio
    async def test_manifest_json(self, client):
        resp = await client.get("/api/manifest.json")
        assert resp.status_code == 200
        data = resp.json()
        assert data["version"] == "1.0"
        assert data["name"] == "bookstore"

    @pytest.mark.asyncio
    async def test_manifest_resources(self, client):
        resp = await client.get("/api/manifest.json")
        data = resp.json()
        names = [r["name"] for r in data["resources"]]
        assert "book" in names
        assert "author" in names
        assert "tag" in names
        assert "review" in names

    @pytest.mark.asyncio
    async def test_manifest_resource_fields(self, client):
        resp = await client.get("/api/manifest.json")
        data = resp.json()
        book = next(r for r in data["resources"] if r["name"] == "book")
        field_names = [f["name"] for f in book["fields"]]
        assert "title" in field_names
        assert "price" in field_names

    @pytest.mark.asyncio
    async def test_manifest_resource_actions(self, client):
        resp = await client.get("/api/manifest.json")
        data = resp.json()
        book = next(r for r in data["resources"] if r["name"] == "book")
        action_names = [a["name"] for a in book["actions"]]
        assert "list" in action_names
        assert "create" in action_names
        assert "in_stock" in action_names

    @pytest.mark.asyncio
    async def test_manifest_pagination_info(self, client):
        resp = await client.get("/api/manifest.json")
        data = resp.json()
        book = next(r for r in data["resources"] if r["name"] == "book")
        assert book["pagination"]["page_size"] == 20

    @pytest.mark.asyncio
    async def test_manifest_filter_info(self, client):
        resp = await client.get("/api/manifest.json")
        data = resp.json()
        book = next(r for r in data["resources"] if r["name"] == "book")
        assert "title" in book["filters"]["search_fields"]

    @pytest.mark.asyncio
    async def test_manifest_mcp_info(self, client):
        resp = await client.get("/api/manifest.json")
        data = resp.json()
        assert data["mcp"]["enabled"] is True
        assert data["mcp"]["prefix"] == "/mcp"

    @pytest.mark.asyncio
    async def test_manifest_skills_info(self, client):
        resp = await client.get("/api/manifest.json")
        data = resp.json()
        assert data["skills"]["enabled"] is True

    @pytest.mark.asyncio
    async def test_manifest_not_in_openapi(self, client):
        resp = await client.get("/openapi.json")
        paths = list(resp.json().get("paths", {}).keys())
        assert "/api/manifest.json" not in paths


class TestAppConfiguration:
    @pytest.mark.asyncio
    async def test_settings_bound_to_app(self, client):
        from app import app
        settings = app.state.fastrest_settings
        assert settings.SKILL_NAME == "bookstore"
        assert settings.SKILL_BASE_URL == "http://localhost:8000/api"
        assert settings.MCP_PREFIX == "/mcp"
