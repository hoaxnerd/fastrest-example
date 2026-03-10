"""Serializers for SQLModel bookstore models."""

from fastrest.serializers import ModelSerializer
from fastrest.fields import FloatField, SerializerMethodField
from fastrest.exceptions import ValidationError

from tests_sqlmodel.models import SMAuthor, SMBook, SMTag, SMReview


class SMAuthorSerializer(ModelSerializer):
    class Meta:
        model = SMAuthor
        fields = ["id", "name", "bio", "is_active"]
        read_only_fields = ["id"]


class SMTagSerializer(ModelSerializer):
    class Meta:
        model = SMTag
        fields = ["id", "name", "slug"]
        read_only_fields = ["id"]


class SMReviewSerializer(ModelSerializer):
    class Meta:
        model = SMReview
        fields = ["id", "book_id", "reviewer_name", "rating", "comment"]
        read_only_fields = ["id"]

    def validate_rating(self, value):
        if not (1 <= value <= 5):
            raise ValidationError("Rating must be between 1 and 5.")
        return value


class SMBookSerializer(ModelSerializer):
    price = FloatField(min_value=0.01)

    class Meta:
        model = SMBook
        fields = ["id", "title", "isbn", "price", "in_stock", "description", "author_id"]
        read_only_fields = ["id"]

    def validate_isbn(self, value):
        if value is not None and len(value) not in (10, 13):
            raise ValidationError("ISBN must be 10 or 13 characters.")
        return value


class SMBookDetailSerializer(SMBookSerializer):
    review_count = SerializerMethodField()

    class Meta(SMBookSerializer.Meta):
        fields = SMBookSerializer.Meta.fields + ["review_count"]

    def get_review_count(self, obj):
        reviews = getattr(obj, "reviews", None)
        if reviews is not None:
            return len(reviews)
        return 0
