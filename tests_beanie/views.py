"""ViewSets for Beanie bookstore models."""

from fastrest.viewsets import ModelViewSet
from fastrest.decorators import action
from fastrest.response import Response
from fastrest.pagination import PageNumberPagination
from fastrest.filters import SearchFilter, OrderingFilter
from fastrest import status

from tests_beanie.models import BAuthor, BBook, BTag, BReview
from tests_beanie.serializers import (
    BAuthorSerializer, BBookSerializer, BTagSerializer, BReviewSerializer,
)


class BAuthorViewSet(ModelViewSet):
    queryset = BAuthor
    serializer_class = BAuthorSerializer
    lookup_field_type = str

    @action(methods=["get"], detail=True, url_path="books")
    async def books(self, request, **kwargs):
        author = await self.get_object()
        books = await self.adapter.filter_queryset(
            BBook, self.get_session(), author_id=str(author.id)
        )
        serializer = BBookSerializer(books, many=True, context=self.get_serializer_context())
        return Response(data=serializer.data)


class BBookPagination(PageNumberPagination):
    page_size = 5
    max_page_size = 100


class BBookViewSet(ModelViewSet):
    queryset = BBook
    serializer_class = BBookSerializer
    lookup_field_type = str
    pagination_class = BBookPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "description", "isbn"]
    ordering_fields = ["title", "price"]
    ordering = ["title"]

    @action(methods=["get"], detail=False, url_path="in-stock")
    async def in_stock(self, request, **kwargs):
        books = await self.adapter.filter_queryset(
            BBook, self.get_session(), in_stock=True
        )
        serializer = self.get_serializer(books, many=True)
        return Response(data=serializer.data)

    @action(methods=["post"], detail=True, url_path="toggle-stock")
    async def toggle_stock(self, request, **kwargs):
        book = await self.get_object()
        session = self.get_session()
        await self.adapter.update(book, session, in_stock=not book.in_stock)
        serializer = self.get_serializer(book)
        return Response(data=serializer.data)


class BTagViewSet(ModelViewSet):
    queryset = BTag
    serializer_class = BTagSerializer
    lookup_field_type = str


class BReviewViewSet(ModelViewSet):
    queryset = BReview
    serializer_class = BReviewSerializer
    lookup_field_type = str
