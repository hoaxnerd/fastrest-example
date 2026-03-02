"""Custom permissions for the bookstore."""

from fastrest.permissions import BasePermission


class IsReviewAuthor(BasePermission):
    """Only allow editing reviews if you're the one who wrote it."""

    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        # Check reviewer_name matches a header (simple auth stand-in)
        return getattr(obj, "reviewer_name", None) == request.headers.get("x-reviewer-name")
