"""Serializers — this is where FastREST should feel like DRF."""

from fastrest.serializers import ModelSerializer, Serializer
from fastrest.fields import CharField, IntegerField, FloatField, SerializerMethodField
from fastrest.exceptions import ValidationError

from models import Author, Book, Tag, Review


class AuthorSerializer(ModelSerializer):
    class Meta:
        model = Author
        fields = ["id", "name", "bio", "is_active"]
        read_only_fields = ["id"]


class TagSerializer(ModelSerializer):
    class Meta:
        model = Tag
        fields = ["id", "name", "slug"]
        read_only_fields = ["id"]


class ReviewSerializer(ModelSerializer):
    class Meta:
        model = Review
        fields = ["id", "book_id", "reviewer_name", "rating", "comment"]
        read_only_fields = ["id"]

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise ValidationError("Rating must be between 1 and 5.")
        return value


class BookSerializer(ModelSerializer):
    # Declared field that overrides auto-generated one
    price = FloatField(min_value=0.01)

    class Meta:
        model = Book
        fields = ["id", "title", "isbn", "price", "in_stock", "description", "author_id"]
        read_only_fields = ["id"]

    def validate_isbn(self, value):
        if value is not None and len(value) not in (10, 13):
            raise ValidationError("ISBN must be 10 or 13 characters.")
        return value


class BookDetailSerializer(BookSerializer):
    """Extended serializer with computed field for detail views."""
    review_count = SerializerMethodField()

    class Meta(BookSerializer.Meta):
        fields = BookSerializer.Meta.fields + ["review_count"]

    def get_review_count(self, obj):
        reviews = getattr(obj, "reviews", None)
        if reviews is not None:
            return len(reviews)
        return 0
