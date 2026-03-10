"""Bookstore domain models using Tortoise ORM."""

from tortoise import fields
from tortoise.models import Model


class TAuthor(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=200)
    bio = fields.TextField(null=True)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "t_authors"


class TTag(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=50)
    slug = fields.CharField(max_length=50)

    class Meta:
        table = "t_tags"


class TBook(Model):
    id = fields.IntField(primary_key=True)
    title = fields.CharField(max_length=300)
    isbn = fields.CharField(max_length=13, null=True)
    price = fields.FloatField()
    in_stock = fields.BooleanField(default=True)
    description = fields.TextField(null=True)
    author = fields.ForeignKeyField("models.TAuthor", related_name="books")

    class Meta:
        table = "t_books"


class TReview(Model):
    id = fields.IntField(primary_key=True)
    book = fields.ForeignKeyField("models.TBook", related_name="reviews")
    reviewer_name = fields.CharField(max_length=100)
    rating = fields.IntField()
    comment = fields.TextField(null=True)

    class Meta:
        table = "t_reviews"
