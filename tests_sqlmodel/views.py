"""ViewSets for SQLModel bookstore models."""

from fastrest.viewsets import ModelViewSet
from fastrest.decorators import action
from fastrest.response import Response
from fastrest.pagination import PageNumberPagination
from fastrest.filters import SearchFilter, OrderingFilter
from fastrest import status

from tests_sqlmodel.models import SMAuthor, SMBook, SMTag, SMReview
from tests_sqlmodel.serializers import (
    SMAuthorSerializer, SMBookSerializer, SMBookDetailSerializer,
    SMTagSerializer, SMReviewSerializer,
)


class SMAuthorViewSet(ModelViewSet):
    queryset = SMAuthor
    serializer_class = SMAuthorSerializer

    @action(methods=["get"], detail=True, url_path="books")
    async def books(self, request, **kwargs):
        author = await self.get_object()
        books = await self.adapter.filter_queryset(
            SMBook, self.get_session(), author_id=author.id
        )
        serializer = SMBookSerializer(books, many=True, context=self.get_serializer_context())
        return Response(data=serializer.data)


class SMBookPagination(PageNumberPagination):
    page_size = 5
    max_page_size = 100


class SMBookViewSet(ModelViewSet):
    queryset = SMBook
    serializer_class = SMBookSerializer
    pagination_class = SMBookPagination
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "description", "isbn"]
    ordering_fields = ["title", "price"]
    ordering = ["title"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return SMBookDetailSerializer
        return SMBookSerializer

    @action(methods=["get"], detail=False, url_path="in-stock")
    async def in_stock(self, request, **kwargs):
        books = await self.adapter.filter_queryset(
            SMBook, self.get_session(), in_stock=True
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


class SMTagViewSet(ModelViewSet):
    queryset = SMTag
    serializer_class = SMTagSerializer


class SMReviewViewSet(ModelViewSet):
    queryset = SMReview
    serializer_class = SMReviewSerializer
