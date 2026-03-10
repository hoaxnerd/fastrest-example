"""Serializers for Beanie bookstore models."""

from fastrest.serializers import ModelSerializer
from fastrest.fields import FloatField, SerializerMethodField
from fastrest.exceptions import ValidationError

from tests_beanie.models import BAuthor, BBook, BTag, BReview


class BAuthorSerializer(ModelSerializer):
    class Meta:
        model = BAuthor
        fields = ["id", "name", "bio", "is_active"]
        read_only_fields = ["id"]


class BTagSerializer(ModelSerializer):
    class Meta:
        model = BTag
        fields = ["id", "name", "slug"]
        read_only_fields = ["id"]


class BReviewSerializer(ModelSerializer):
    class Meta:
        model = BReview
        fields = ["id", "book_id", "reviewer_name", "rating", "comment"]
        read_only_fields = ["id"]

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise ValidationError("Rating must be between 1 and 5.")
        return value


class BBookSerializer(ModelSerializer):
    price = FloatField(min_value=0.01)

    class Meta:
        model = BBook
        fields = ["id", "title", "isbn", "price", "in_stock", "description", "author_id"]
        read_only_fields = ["id"]

    def validate_isbn(self, value):
        if value is not None and len(value) not in (10, 13):
            raise ValidationError("ISBN must be 10 or 13 characters.")
        return value
