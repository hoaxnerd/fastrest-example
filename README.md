# FastREST Example — Bookstore API

A complete example application built with [FastREST](https://github.com/hoaxnerd/fastrest), demonstrating how to build a full-featured async REST API using DRF-style patterns on FastAPI.

## Examples

This repo contains multiple example apps showing different ways to use FastREST:

| Example | What it shows |
|---------|--------------|
| **[Main app](#main-app)** (`app.py`) | Full bookstore with serializers, viewsets, custom actions, auth, throttling, permissions, MCP, SKILL.md |
| **[Zero-config](#zero-config-serve)** (`examples/serve_quickstart/`) | `router.serve(Model)` — full CRUD from models in ~30 lines |
| **[Advanced](#advanced-example)** (`examples/advanced/`) | Permission composition (`&`, `\|`, `~`), scopes, multiple auth backends, rate limiting, full agent customization |
| **[Tortoise ORM](#tortoise-orm)** (`examples/tortoise_app/`) | Session-less REST API with Tortoise ORM |
| **[Beanie (MongoDB)](#beanie-mongodb)** (`examples/beanie_app/`) | Document-based REST API with auto string PK detection |
| **[SQLModel](#sqlmodel)** (`examples/sqlmodel_app/`) | Pydantic-native models with explicit adapter setup |

### Per-ORM test suites

Full test coverage for each ORM backend:

| Directory | ORM | Tests |
|-----------|-----|-------|
| `tests/` | SQLAlchemy | CRUD, pagination, search, ordering, auth, throttle, OpenAPI, agent integration, serve() |
| `tests_sqlmodel/` | SQLModel | CRUD, pagination, serve() |
| `tests_tortoise/` | Tortoise ORM | CRUD, pagination, serve() |
| `tests_beanie/` | Beanie (MongoDB) | CRUD, pagination, serve() |

---

## Main App

The primary bookstore API with four resources:

| Resource | Endpoints | Features |
|---|---|---|
| **Authors** | CRUD + `GET /authors/{id}/books` | Custom `@action` with MCP description, agent skill examples |
| **Books** | CRUD + `toggle-stock`, `in-stock` | Pagination, search, ordering, throttling, `get_serializer_class()`, SKILL.md customization |
| **Tags** | CRUD | Basic ModelViewSet |
| **Reviews** | CRUD | Auth required for writes, permission composition (`IsAuthenticatedOrReadOnly & (IsReviewAuthor \| IsAdminUser)`), field-level validation, `skill_exclude_actions` |

### Quick start

```bash
git clone https://github.com/hoaxnerd/fastrest-example.git
cd fastrest-example
pip install -r requirements.txt
uvicorn app:app --reload
```

Then visit:
- `http://localhost:8000/docs` — Swagger UI
- `http://localhost:8000/api/` — API root
- `http://localhost:8000/api/SKILL.md` — Agent skill document
- `http://localhost:8000/api/manifest.json` — API manifest
- `http://localhost:8000/api/books/SKILL.md` — Per-resource agent docs

### Demo tokens

```bash
# Admin (full access)
curl -H "Authorization: Bearer admin-token-001" http://localhost:8000/api/reviews

# Regular user
curl -H "Authorization: Bearer user-token-002" http://localhost:8000/api/reviews
```

### API highlights

```bash
# Pagination
GET /api/books                    → {"count": 42, "next": "?page=2", "results": [...]}
GET /api/books?page=2&page_size=5

# Search & Ordering
GET /api/books?search=django
GET /api/books?ordering=-price
GET /api/books?search=web&ordering=-price&page_size=5

# Custom actions
POST /api/books/{id}/toggle-stock
GET  /api/books/in-stock
GET  /api/authors/{id}/books

# Agent endpoints
GET  /api/SKILL.md
GET  /api/books/SKILL.md
GET  /api/manifest.json
```

---

## Zero-Config Serve

The fastest way to go from models to API — one line per model:

```python
# examples/serve_quickstart/app.py
router = DefaultRouter()
router.serve(Author)
router.serve(Book,
    pagination_class=BookPagination,
    filter_backends=[SearchFilter, OrderingFilter],
    search_fields=["title", "description"],
    ordering_fields=["title", "price"],
)
router.serve(Category, readonly=True)
```

Run:
```bash
uvicorn examples.serve_quickstart.app:app --reload
```

---

## Advanced Example

Demonstrates permission composition, scoped access, multiple auth backends, and full agent customization:

```python
# examples/advanced/app.py

# Permission composition with & | operators
permission_classes = [IsAuthenticated() & (IsOwner() | IsAdminUser())]

# Scope-based access control
permission_classes = [IsAuthenticated() & HasScope("articles:publish")]

# Multiple auth backends
authentication_classes = [token_auth, basic_auth]

# Different throttles for anon vs authenticated
throttle_classes = [CommentAnonThrottle(), CommentUserThrottle()]

# Custom @action with MCP control
@action(methods=["post"], detail=True, url_path="publish",
        mcp_description="Publish a draft article")
async def publish(self, request, **kwargs):
    ...

@action(methods=["post"], detail=True, url_path="archive", mcp=False)  # hidden from MCP
async def archive(self, request, **kwargs):
    ...

# Full SKILL.md customization
skill_description = "Manage articles with drafts, publishing, and featuring."
skill_exclude_fields = ["owner_id"]
skill_exclude_actions = ["destroy"]
skill_examples = [
    {"description": "Search articles", "request": "GET /articles?search=python", "response": "200"},
]

# Full app configuration
configure(app, {
    "SKILL_NAME": "advanced-api",
    "SKILL_BASE_URL": "http://localhost:8000/api",
    "SKILL_DESCRIPTION": "An article CMS with scoped permissions and rate limiting.",
    "SKILL_AUTH_DESCRIPTION": "Use Bearer token: admin-secret, editor-secret, or viewer-secret.",
    "MCP_ENABLED": True,
    "MCP_PREFIX": "/mcp",
    "DEFAULT_AUTHENTICATION_CLASSES": [token_auth],
    "DEFAULT_PERMISSION_CLASSES": [IsAuthenticatedOrReadOnly],
})
```

Three demo tokens with different scopes:
- `admin-secret` — admin, scopes: `articles:read`, `articles:write`, `articles:publish`
- `editor-secret` — editor, scopes: `articles:read`, `articles:write`
- `viewer-secret` — viewer, scopes: `articles:read`

Run:
```bash
uvicorn examples.advanced.app:app --reload
```

---

## Tortoise ORM

Session-less REST API — Tortoise manages connections internally:

```python
# examples/tortoise_app/app.py
set_default_adapter(TortoiseAdapter())

router = DefaultRouter()
router.serve(Author)
router.serve(Book, filter_backends=[SearchFilter, OrderingFilter], ...)
router.serve(Category, readonly=True)

app.include_router(router.urls, prefix="/api")
# No session middleware needed
```

Run:
```bash
pip install fastrest[tortoise] aiosqlite uvicorn
uvicorn examples.tortoise_app.app:app --reload
```

---

## Beanie (MongoDB)

Document-based REST API with auto string PK detection:

```python
# examples/beanie_app/app.py
set_default_adapter(BeanieAdapter())

router = DefaultRouter()
router.serve(Author)    # auto-detects string PK for MongoDB ObjectIds
router.serve(Book, ...)
router.serve(Tag, readonly=True)
```

Run:
```bash
pip install fastrest[beanie] uvicorn
# Requires running MongoDB instance
uvicorn examples.beanie_app.app:app --reload
```

---

## SQLModel

Pydantic-native models — must set adapter explicitly:

```python
# examples/sqlmodel_app/app.py
set_default_adapter(SQLModelAdapter())  # required — SQLModel co-installs SQLAlchemy

router = DefaultRouter()
router.serve(Author)
router.serve(Book, ...)
router.serve(Category, readonly=True)
```

Run:
```bash
pip install fastrest[sqlmodel] aiosqlite uvicorn
uvicorn examples.sqlmodel_app.app:app --reload
```

---

## Project Structure

```
app.py                          # Main bookstore API (SQLAlchemy, full features)
models.py                       # SQLAlchemy models
serializers.py                  # DRF-style ModelSerializers with validation
views.py                        # ViewSets with pagination, filters, auth, throttle, agent customization
authentication.py               # Token auth with demo tokens
permissions.py                  # Custom permission classes
db.py                           # Async SQLAlchemy engine and session
run.sh                          # Quick start script

examples/
  serve_quickstart/app.py       # router.serve() — zero-config in ~30 lines
  advanced/app.py               # Permissions, scopes, throttling, full agent config
  tortoise_app/app.py           # Tortoise ORM — session-less
  beanie_app/app.py             # Beanie (MongoDB) — string PK
  sqlmodel_app/app.py           # SQLModel — explicit adapter

tests/                          # SQLAlchemy tests (CRUD, auth, throttle, OpenAPI, agent, serve)
tests_sqlmodel/                 # SQLModel tests (CRUD, pagination, serve)
tests_tortoise/                 # Tortoise tests (CRUD, pagination, serve)
tests_beanie/                   # Beanie tests (CRUD, pagination, serve)
```

## Running Tests

```bash
# All tests
pytest tests/ tests_sqlmodel/ tests_tortoise/ tests_beanie/ -v

# Just main app
pytest tests/ -v

# Just one ORM
pytest tests_tortoise/ -v
```

## Requirements

- Python 3.10+
- [fastrest](https://github.com/hoaxnerd/fastrest) >= 0.1.3

## License

BSD 3-Clause. See [LICENSE](LICENSE).
