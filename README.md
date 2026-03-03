# FastREST Example — Bookstore API

A complete example application built with [FastREST](https://github.com/hoaxnerd/fastrest), demonstrating how to build a full-featured async REST API using DRF-style patterns on FastAPI.

## What's in the box

A bookstore API with four resources:

| Resource | Endpoints | Features demonstrated |
|---|---|---|
| **Authors** | CRUD + `GET /authors/{id}/books` | Custom `@action`, relationships |
| **Books** | CRUD + `toggle-stock`, `in-stock` | Pagination, search, ordering, custom actions, `get_serializer_class()` |
| **Tags** | CRUD | Basic ModelViewSet |
| **Reviews** | CRUD | Field-level validation (`validate_rating`) |

## Project structure

```
app.py              # FastAPI app with router setup and DB middleware
models.py           # SQLAlchemy models (Author, Book, Tag, Review)
serializers.py      # DRF-style ModelSerializers with validation
views.py            # ViewSets with pagination, filters, and custom actions
db.py               # Async SQLAlchemy engine and session factory
permissions.py      # Custom permission classes
tests/              # 53 async tests covering all endpoints
```

## Quick start

```bash
# Clone the repo
git clone https://github.com/hoaxnerd/fastrest-example.git
cd fastrest-example

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app:app --reload
```

Then visit:
- `http://localhost:8000/docs` — Swagger UI
- `http://localhost:8000/redoc` — ReDoc
- `http://localhost:8000/api/` — API root

## API highlights

### Pagination

Books are paginated with 20 items per page:

```
GET /api/books                  → {"count": 42, "next": "?page=2", "previous": null, "results": [...]}
GET /api/books?page=2           → second page
GET /api/books?page_size=10     → custom page size (max 100)
```

### Search & Ordering

```
GET /api/books?search=django        → search across title, description, isbn
GET /api/books?ordering=-price      → sort by price descending
GET /api/books?ordering=title       → sort by title ascending
GET /api/books?search=web&ordering=-price&page_size=5  → combined
```

### Custom actions

```
POST /api/books/{id}/toggle-stock   → toggle in_stock flag
GET  /api/books/in-stock            → list only in-stock books
GET  /api/authors/{id}/books        → list books by author
```

## Running tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

All 53 tests run against an in-memory SQLite database — no external services needed.

## Requirements

- Python 3.10+
- [fastrest](https://github.com/hoaxnerd/fastrest) (installed via requirements.txt)

## License

BSD 3-Clause. See [LICENSE](LICENSE).
