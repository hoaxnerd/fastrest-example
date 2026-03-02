"""ViewSets — wiring serializers to HTTP endpoints."""

from fastrest.viewsets import ModelViewSet, ReadOnlyModelViewSet
from fastrest.decorators import action
from fastrest.response import Response
from fastrest.permissions import AllowAny
from fastrest import status

from example.models import Author, Book, Tag, Review
from example.serializers import (
    AuthorSerializer,
    BookSerializer,
    BookDetailSerializer,
    TagSerializer,
    ReviewSerializer,
)


class AuthorViewSet(ModelViewSet):
    queryset = Author
    serializer_class = AuthorSerializer

    @action(methods=["get"], detail=True, url_path="books")
    async def books(self, request, **kwargs):
        """List all books by this author."""
        author = await self.get_object()
        books = await self.adapter.filter_queryset(
            Book, self.get_session(), author_id=author.id
        )
        serializer = BookSerializer(books, many=True, context=self.get_serializer_context())
        return Response(data=serializer.data)


class BookViewSet(ModelViewSet):
    queryset = Book
    serializer_class = BookSerializer

    def get_serializer_class(self):
        if self.action == "retrieve":
            return BookDetailSerializer
        return BookSerializer

    @action(methods=["get"], detail=False, url_path="in-stock")
    async def in_stock(self, request, **kwargs):
        """List only books that are in stock."""
        books = await self.adapter.filter_queryset(
            Book, self.get_session(), in_stock=True
        )
        serializer = self.get_serializer(books, many=True)
        return Response(data=serializer.data)

    @action(methods=["post"], detail=True, url_path="toggle-stock")
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


class ReviewViewSet(ModelViewSet):
    queryset = Review
    serializer_class = ReviewSerializer

    def validate_and_set_book(self, serializer):
        """Example of perform_create override to add extra logic."""
        pass

    async def perform_create(self, serializer):
        # Could add extra logic here like notifying the book author
        await serializer.save()
