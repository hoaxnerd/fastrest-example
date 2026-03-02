"""Tests for OpenAPI schema generation and docs endpoints."""

import pytest


@pytest.mark.asyncio
async def test_openapi_json_returns_200(client):
    resp = await client.get("/openapi.json")
    assert resp.status_code == 200
    data = resp.json()
    assert "openapi" in data
    assert "paths" in data


@pytest.mark.asyncio
async def test_docs_returns_200(client):
    resp = await client.get("/docs")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_redoc_returns_200(client):
    resp = await client.get("/redoc")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_response_schemas_have_field_names(client):
    resp = await client.get("/openapi.json")
    schemas = resp.json().get("components", {}).get("schemas", {})
    # Should have response models with correct field names
    author_schema = schemas.get("AuthorResponse")
    assert author_schema is not None
    props = author_schema["properties"]
    assert "id" in props
    assert "name" in props
    assert "bio" in props
    assert "is_active" in props


@pytest.mark.asyncio
async def test_response_schemas_have_correct_types(client):
    resp = await client.get("/openapi.json")
    schemas = resp.json().get("components", {}).get("schemas", {})
    author_schema = schemas.get("AuthorResponse")
    assert author_schema is not None
    props = author_schema["properties"]
    assert props["id"]["type"] == "integer"
    assert props["name"]["type"] == "string"
    # is_active may be nullable (anyOf boolean|null) or plain boolean
    if "anyOf" in props["is_active"]:
        types = [t.get("type") for t in props["is_active"]["anyOf"]]
        assert "boolean" in types
    else:
        assert props["is_active"]["type"] == "boolean"


@pytest.mark.asyncio
async def test_request_body_schemas_for_post(client):
    resp = await client.get("/openapi.json")
    paths = resp.json()["paths"]
    # POST /api/authors should have a requestBody
    author_post = paths.get("/api/authors", {}).get("post", {})
    assert "requestBody" in author_post


@pytest.mark.asyncio
async def test_request_body_schemas_for_put(client):
    resp = await client.get("/openapi.json")
    paths = resp.json()["paths"]
    # PUT /api/authors/{pk} should have a requestBody
    author_put = paths.get("/api/authors/{pk}", {}).get("put", {})
    assert "requestBody" in author_put


@pytest.mark.asyncio
async def test_request_body_schemas_for_patch(client):
    resp = await client.get("/openapi.json")
    paths = resp.json()["paths"]
    author_patch = paths.get("/api/authors/{pk}", {}).get("patch", {})
    assert "requestBody" in author_patch


@pytest.mark.asyncio
async def test_status_code_201_for_create(client):
    resp = await client.get("/openapi.json")
    paths = resp.json()["paths"]
    author_post = paths.get("/api/authors", {}).get("post", {})
    assert "201" in author_post.get("responses", {})


@pytest.mark.asyncio
async def test_status_code_204_for_destroy(client):
    resp = await client.get("/openapi.json")
    paths = resp.json()["paths"]
    author_delete = paths.get("/api/authors/{pk}", {}).get("delete", {})
    assert "204" in author_delete.get("responses", {})


@pytest.mark.asyncio
async def test_status_code_200_for_list(client):
    resp = await client.get("/openapi.json")
    paths = resp.json()["paths"]
    author_get = paths.get("/api/authors", {}).get("get", {})
    assert "200" in author_get.get("responses", {})


@pytest.mark.asyncio
async def test_status_code_200_for_retrieve(client):
    resp = await client.get("/openapi.json")
    paths = resp.json()["paths"]
    author_get = paths.get("/api/authors/{pk}", {}).get("get", {})
    assert "200" in author_get.get("responses", {})


@pytest.mark.asyncio
async def test_unique_operation_ids(client):
    resp = await client.get("/openapi.json")
    paths = resp.json()["paths"]
    operation_ids = []
    for path, methods in paths.items():
        for method, details in methods.items():
            if isinstance(details, dict) and "operationId" in details:
                operation_ids.append(details["operationId"])
    # All operation IDs should be unique
    assert len(operation_ids) == len(set(operation_ids)), f"Duplicate operation IDs: {operation_ids}"


@pytest.mark.asyncio
async def test_endpoints_grouped_by_tags(client):
    resp = await client.get("/openapi.json")
    paths = resp.json()["paths"]
    # Check that /api/authors endpoints have "authors" tag
    for method_info in paths.get("/api/authors", {}).values():
        if isinstance(method_info, dict) and "tags" in method_info:
            assert "authors" in method_info["tags"]
    # Check that /api/books endpoints have "books" tag
    for method_info in paths.get("/api/books", {}).values():
        if isinstance(method_info, dict) and "tags" in method_info:
            assert "books" in method_info["tags"]


@pytest.mark.asyncio
async def test_pk_typed_as_integer(client):
    resp = await client.get("/openapi.json")
    paths = resp.json()["paths"]
    # /api/authors/{pk} GET should have pk as integer
    author_get = paths.get("/api/authors/{pk}", {}).get("get", {})
    params = author_get.get("parameters", [])
    pk_params = [p for p in params if p["name"] == "pk"]
    assert len(pk_params) == 1
    assert pk_params[0]["schema"]["type"] == "integer"


@pytest.mark.asyncio
async def test_custom_action_endpoints_in_schema(client):
    resp = await client.get("/openapi.json")
    paths = resp.json()["paths"]
    # The @action(detail=True) "books" on AuthorViewSet
    assert "/api/authors/{pk}/books" in paths
    # The @action(detail=False) "in-stock" on BookViewSet
    assert "/api/books/in-stock" in paths
    # The @action(detail=True) "toggle-stock" on BookViewSet
    assert "/api/books/{pk}/toggle-stock" in paths
