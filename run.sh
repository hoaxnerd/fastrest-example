#!/bin/bash
# Run the FastREST example bookstore API.
# Usage: ./run.sh
#
# Prerequisites:
#   pip install fastrest[sqlalchemy,mcp] aiosqlite uvicorn
#
# The server starts at http://localhost:8000
# Swagger UI at http://localhost:8000/docs
# API root at http://localhost:8000/api/
#
# Demo tokens (for auth-gated endpoints like reviews):
#   Admin: Authorization: Bearer admin-token-001
#   User:  Authorization: Bearer user-token-002
#
# Quick test after starting:
#
#   # Create an author
#   curl -X POST http://localhost:8000/api/authors \
#     -H "Content-Type: application/json" \
#     -d '{"name":"Ursula K. Le Guin","bio":"Science fiction author"}'
#
#   # Create a book
#   curl -X POST http://localhost:8000/api/books \
#     -H "Content-Type: application/json" \
#     -d '{"title":"The Left Hand of Darkness","isbn":"0441478123","price":12.99,"author_id":1}'
#
#   # Search books
#   curl "http://localhost:8000/api/books?search=darkness"
#
#   # Create a review (requires auth)
#   curl -X POST http://localhost:8000/api/reviews \
#     -H "Content-Type: application/json" \
#     -H "Authorization: Bearer admin-token-001" \
#     -d '{"book_id":1,"reviewer_name":"Alice","rating":5,"comment":"Masterpiece"}'
#
#   # Agent endpoints
#   curl http://localhost:8000/api/SKILL.md
#   curl http://localhost:8000/api/manifest.json

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting Bookstore API at http://localhost:8000"
echo "Swagger UI: http://localhost:8000/docs"
echo "API root:   http://localhost:8000/api/"
echo ""
echo "Press Ctrl+C to stop."
echo ""

python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
