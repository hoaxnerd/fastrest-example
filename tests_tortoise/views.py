"""ViewSets for Tortoise bookstore models."""

from fastrest.viewsets import ModelViewSet
from fastrest.decorators import action
from fastrest.response import Response
from fastrest.pagination import PageNumberPagination
from fastrest.filters import SearchFilter, OrderingFilter
from fastrest import status

from tests_tortoise.models import TAuthor, TBook, TTag, TReview
from tests_tortoise.serializers import (
    TAuthorSerializer, TBookSerializer, TTagSerializer, TReviewSerializer,
)


class TAuthorViewSet(ModelViewSet):
    queryset = TAuthor
    serializer_class = TAuthorSerializer

    @action(methods=["get"], detail=True, url_path="books")
    async def books(self, request, **kwargs):
        author = await self.get_object()
        books = await self.adapter.filter_queryset(
            TBook, self.get_session(), author_id=author.id
        )
        serializer = TBookSerializer(books, many=True, context=self.get_serializer_context())
        return Response(data=serializer.data)


class TBookPagination(PageNumberPagination):
    page_size = 5
    max_page_size = 100


class TBookViewSet(ModelViewSet):
    queryset = TBook
    serializer_class = TBookSerializer
    pagination_class = TBookPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "description", "isbn"]
    ordering_fields = ["title", "price"]
    ordering = ["title"]

    @action(methods=["get"], detail=False, url_path="in-stock")
    async def in_stock(self, request, **kwargs):
        books = await self.adapter.filter_queryset(
            TBook, self.get_session(), in_stock=True
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


class TTagViewSet(ModelViewSet):
    queryset = TTag
    serializer_class = TTagSerializer


class TReviewViewSet(ModelViewSet):
    queryset = TReview
    serializer_class = TReviewSerializer
