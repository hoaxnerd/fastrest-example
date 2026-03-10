"""ViewSets — wiring serializers to HTTP endpoints."""

from fastrest.viewsets import ModelViewSet, ReadOnlyModelViewSet
from fastrest.decorators import action
from fastrest.response import Response
from fastrest.permissions import AllowAny, IsAuthenticated, IsAdminUser, IsAuthenticatedOrReadOnly
from fastrest.pagination import PageNumberPagination
from fastrest.filters import SearchFilter, OrderingFilter
from fastrest.throttling import SimpleRateThrottle
from fastrest import status

from models import Author, Book, Tag, Review
from serializers import (
    AuthorSerializer,
    BookSerializer,
    BookDetailSerializer,
    TagSerializer,
    ReviewSerializer,
)
from authentication import token_auth
from permissions import IsReviewAuthor


class AuthorViewSet(ModelViewSet):
    queryset = Author
    serializer_class = AuthorSerializer

    # Agent integration — customize how this resource appears in SKILL.md
    skill_description = "Manage authors in the bookstore catalog."
    skill_examples = [
        {
            "description": "List all active authors",
            "request": "GET /authors",
            "response": "200",
        },
    ]

    @action(methods=["get"], detail=True, url_path="books",
            mcp_description="List all books written by this author")
    async def books(self, request, **kwargs):
        """List all books by this author."""
        author = await self.get_object()
        books = await self.adapter.filter_queryset(
            Book, self.get_session(), author_id=author.id
        )
        serializer = BookSerializer(books, many=True, context=self.get_serializer_context())
        return Response(data=serializer.data)


class BookRateThrottle(SimpleRateThrottle):
    rate = "100/min"

    def get_cache_key(self, request, view):
        return f"book_{self.get_ident(request)}"


class BookPagination(PageNumberPagination):
    page_size = 20
    max_page_size = 100


class BookViewSet(ModelViewSet):
    queryset = Book
    serializer_class = BookSerializer
    pagination_class = BookPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "description", "isbn"]
    ordering_fields = ["title", "price"]
    ordering = ["title"]
    throttle_classes = [BookRateThrottle]

    # Agent integration — full customization
    skill_description = "Manage the book catalog with search, filtering, and stock management."
    skill_exclude_fields = ["author_id"]  # hide internal FK from agent docs
    skill_examples = [
        {
            "description": "Search for books about Python",
            "request": "GET /books?search=python",
            "response": "200",
        },
        {
            "description": "List books ordered by price (cheapest first)",
            "request": "GET /books?ordering=price",
            "response": "200",
        },
    ]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return BookDetailSerializer
        return BookSerializer

    @action(methods=["get"], detail=False, url_path="in-stock",
            mcp_description="List only books that are currently in stock")
    async def in_stock(self, request, **kwargs):
        """List only books that are in stock."""
        books = await self.adapter.filter_queryset(
            Book, self.get_session(), in_stock=True
        )
        serializer = self.get_serializer(books, many=True)
        return Response(data=serializer.data)

    @action(methods=["post"], detail=True, url_path="toggle-stock",
            mcp_description="Toggle whether a book is marked as in stock")
    async def toggle_stock(self, request, **kwargs):
        """Toggle the in_stock flag."""
        book = await self.get_object()
        session = self.get_session()
        await self.adapter.update(book, session, in_stock=not book.in_stock)
        serializer = self.get_serializer(book)
        return Response(data=serializer.data)


class TagViewSet(ModelViewSet):
    queryset = Tag
    serializer_class = TagSerializer
    skill_description = "Manage tags for categorizing books."


class ReviewViewSet(ModelViewSet):
    queryset = Review
    serializer_class = ReviewSerializer
    authentication_classes = [token_auth]

    # Permission composition with & and | operators:
    # Reads are public, writes require auth AND (be the review author OR admin)
    permission_classes = [IsAuthenticatedOrReadOnly() & (IsReviewAuthor() | IsAdminUser())]

    # Agent integration
    skill_description = "Read and write book reviews. Writing requires authentication."
    skill_exclude_actions = ["destroy"]  # don't advertise delete to agents

    async def perform_create(self, serializer):
        # Could add extra logic here like notifying the book author
        await serializer.save()
