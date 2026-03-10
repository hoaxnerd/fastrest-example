"""
Advanced FastREST example — authentication, permissions, throttling, scopes,
content negotiation, MCP, SKILL.md, and full app configuration.

Demonstrates:
    - Permission composition with &, |, ~ operators
    - HasScope for scope-based access control
    - Multiple authentication backends
    - Rate limiting with AnonRateThrottle and UserRateThrottle
    - Custom @action with MCP/SKILL.md integration
    - Full app configuration via configure()
    - Content negotiation
    - Custom permission classes

Run:
    pip install fastrest[sqlalchemy,mcp] aiosqlite uvicorn
    uvicorn examples.advanced.app:app --reload

Try:
    # Public — list articles (no auth needed)
    curl http://localhost:8000/api/articles

    # Auth required — create an article
    curl -X POST http://localhost:8000/api/articles \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer admin-secret" \
      -d '{"title":"Hello World","body":"My first post","status":"draft","owner_id":1}'

    # Agent endpoints
    curl http://localhost:8000/api/SKILL.md
    curl http://localhost:8000/api/manifest.json
    curl http://localhost:8000/api/articles/SKILL.md
"""

from fastapi import FastAPI, Request
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from fastrest.routers import DefaultRouter
from fastrest.viewsets import ModelViewSet, ReadOnlyModelViewSet
from fastrest.serializers import ModelSerializer
from fastrest.fields import CharField, IntegerField, SerializerMethodField
from fastrest.decorators import action
from fastrest.response import Response
from fastrest.exceptions import ValidationError
from fastrest.permissions import (
    BasePermission, AllowAny, IsAuthenticated, IsAdminUser,
    IsAuthenticatedOrReadOnly, HasScope,
)
from fastrest.authentication import TokenAuthentication, BasicAuthentication
from fastrest.throttling import SimpleRateThrottle, AnonRateThrottle, UserRateThrottle
from fastrest.pagination import PageNumberPagination, LimitOffsetPagination
from fastrest.filters import SearchFilter, OrderingFilter
from fastrest.settings import configure
from fastrest.mcp import mount_mcp


# ════════════════════════════════════════════════════════════════════
# MODELS
# ════════════════════════════════════════════════════════════════════

class Base(DeclarativeBase):
    pass


class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(20), default="draft")  # draft, published, archived
    owner_id = Column(Integer, nullable=False)
    is_featured = Column(Boolean, default=False)


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)
    author_name = Column(String(100), nullable=False)
    body = Column(Text, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    action = Column(String(50), nullable=False)
    resource = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)


# ════════════════════════════════════════════════════════════════════
# AUTHENTICATION
# ════════════════════════════════════════════════════════════════════

class User:
    """Simple user object for demo."""
    def __init__(self, id, username, is_staff=False, scopes=None):
        self.id = id
        self.username = username
        self.is_staff = is_staff
        self.scopes = scopes or []

    def __bool__(self):
        return True


# Token store — in production, look these up from a database
TOKENS = {
    "admin-secret": User(1, "admin", is_staff=True, scopes=["articles:read", "articles:write", "articles:publish"]),
    "editor-secret": User(2, "editor", scopes=["articles:read", "articles:write"]),
    "viewer-secret": User(3, "viewer", scopes=["articles:read"]),
}

BASIC_USERS = {
    ("admin", "password123"): User(1, "admin", is_staff=True, scopes=["articles:read", "articles:write"]),
}


def get_user_by_token(key):
    return TOKENS.get(key)


def get_user_by_credentials(username, password):
    return BASIC_USERS.get((username, password))


# Two auth backends — token and basic
token_auth = TokenAuthentication(get_user_by_token=get_user_by_token, keyword="Bearer")
basic_auth = BasicAuthentication(get_user_by_credentials=get_user_by_credentials)


# ════════════════════════════════════════════════════════════════════
# CUSTOM PERMISSIONS
# ════════════════════════════════════════════════════════════════════

class IsOwner(BasePermission):
    """Only allow the article owner to modify it."""

    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return hasattr(request, "user") and getattr(obj, "owner_id", None) == getattr(request.user, "id", None)


# ════════════════════════════════════════════════════════════════════
# THROTTLING
# ════════════════════════════════════════════════════════════════════

class ArticleBurstThrottle(SimpleRateThrottle):
    """Burst rate limit — 30 requests per minute."""
    rate = "30/min"

    def get_cache_key(self, request, view):
        return f"article_burst_{self.get_ident(request)}"


class CommentAnonThrottle(AnonRateThrottle):
    """Limit anonymous comment readers to 60/hour."""
    rate = "60/hour"


class CommentUserThrottle(UserRateThrottle):
    """Limit authenticated comment authors to 20/min."""
    rate = "20/min"


# ════════════════════════════════════════════════════════════════════
# SERIALIZERS
# ════════════════════════════════════════════════════════════════════

class ArticleSerializer(ModelSerializer):
    title = CharField(max_length=300, min_length=5)

    class Meta:
        model = Article
        fields = ["id", "title", "body", "status", "owner_id", "is_featured"]
        read_only_fields = ["id"]

    def validate_status(self, value):
        if value not in ("draft", "published", "archived"):
            raise ValidationError("Status must be draft, published, or archived.")
        return value

    def validate(self, attrs):
        """Object-level validation: featured articles must be published."""
        if attrs.get("is_featured") and attrs.get("status") != "published":
            raise ValidationError("Only published articles can be featured.")
        return attrs


class ArticleListSerializer(ModelSerializer):
    """Lighter serializer for list views — omits body."""
    class Meta:
        model = Article
        fields = ["id", "title", "status", "owner_id", "is_featured"]
        read_only_fields = ["id"]


class CommentSerializer(ModelSerializer):
    class Meta:
        model = Comment
        fields = ["id", "article_id", "author_name", "body"]
        read_only_fields = ["id"]

    def validate_body(self, value):
        if len(value.strip()) < 10:
            raise ValidationError("Comments must be at least 10 characters.")
        return value


# ════════════════════════════════════════════════════════════════════
# PAGINATION
# ════════════════════════════════════════════════════════════════════

class ArticlePagination(PageNumberPagination):
    page_size = 10
    max_page_size = 50


class CommentPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 100


# ════════════════════════════════════════════════════════════════════
# VIEWSETS
# ════════════════════════════════════════════════════════════════════

class ArticleViewSet(ModelViewSet):
    queryset = Article
    serializer_class = ArticleSerializer

    # Auth — supports both token and basic auth
    authentication_classes = [token_auth, basic_auth]

    # Permissions — composed with operators:
    # Must be authenticated AND (be the owner OR be admin)
    permission_classes = [IsAuthenticated() & (IsOwner() | IsAdminUser())]

    # Throttling
    throttle_classes = [ArticleBurstThrottle()]

    # Pagination
    pagination_class = ArticlePagination

    # Filtering
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "body"]
    ordering_fields = ["title", "status"]
    ordering = ["-id"]

    # Agent customization
    skill_description = "Manage articles with drafts, publishing, and featuring. Requires authentication."
    skill_exclude_fields = ["owner_id"]
    skill_examples = [
        {
            "description": "Search for articles about Python",
            "request": "GET /articles?search=python",
            "response": "200",
        },
        {
            "description": "Create a draft article",
            "request": "POST /articles",
            "response": "201",
        },
    ]

    def get_serializer_class(self):
        """Use lighter serializer for list views."""
        if self.action == "list":
            return ArticleListSerializer
        return ArticleSerializer

    @action(methods=["post"], detail=True, url_path="publish",
            mcp_description="Publish a draft article, making it visible to readers")
    async def publish(self, request, **kwargs):
        """POST /api/articles/{pk}/publish — Publish a draft article."""
        article = await self.get_object()
        if article.status != "draft":
            return Response(
                data={"detail": "Only draft articles can be published."},
                status=400,
            )
        session = self.get_session()
        await self.adapter.update(article, session, status="published")
        serializer = self.get_serializer(article)
        return Response(data=serializer.data)

    @action(methods=["post"], detail=True, url_path="archive", mcp=False)
    async def archive(self, request, **kwargs):
        """POST /api/articles/{pk}/archive — Archive (hidden from MCP tools)."""
        article = await self.get_object()
        session = self.get_session()
        await self.adapter.update(article, session, status="archived")
        serializer = self.get_serializer(article)
        return Response(data=serializer.data)

    @action(methods=["get"], detail=False, url_path="published")
    async def published(self, request, **kwargs):
        """GET /api/articles/published — List only published articles."""
        articles = await self.adapter.filter_queryset(
            Article, self.get_session(), status="published"
        )
        serializer = ArticleListSerializer(articles, many=True, context=self.get_serializer_context())
        return Response(data=serializer.data)

    @action(methods=["get"], detail=False, url_path="featured")
    async def featured(self, request, **kwargs):
        """GET /api/articles/featured — List featured articles."""
        articles = await self.adapter.filter_queryset(
            Article, self.get_session(), is_featured=True
        )
        serializer = ArticleListSerializer(articles, many=True, context=self.get_serializer_context())
        return Response(data=serializer.data)


class CommentViewSet(ModelViewSet):
    queryset = Comment
    serializer_class = CommentSerializer

    # Public reads, authenticated writes
    authentication_classes = [token_auth]
    permission_classes = [IsAuthenticatedOrReadOnly]

    # Different throttles for anon vs authenticated
    throttle_classes = [CommentAnonThrottle(), CommentUserThrottle()]

    # Pagination — limit/offset style
    pagination_class = CommentPagination

    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["author_name", "body"]
    ordering_fields = ["id", "author_name"]

    skill_description = "Read and post comments on articles."


class AuditLogViewSet(ReadOnlyModelViewSet):
    """Read-only audit logs — scope-gated access."""
    queryset = AuditLog
    serializer_class = type("AuditLogSerializer", (ModelSerializer,), {
        "Meta": type("Meta", (), {
            "model": AuditLog,
            "fields": ["id", "action", "resource", "details"],
            "read_only_fields": ["id"],
        }),
    })
    authentication_classes = [token_auth]
    # Only users with the 'articles:publish' scope can view audit logs
    permission_classes = [IsAuthenticated() & HasScope("articles:publish")]

    skill_description = "View audit logs. Requires articles:publish scope."
    skill_exclude_actions = ["create", "update", "partial_update", "destroy"]


# ════════════════════════════════════════════════════════════════════
# ROUTER & APP
# ════════════════════════════════════════════════════════════════════

router = DefaultRouter()
router.register("articles", ArticleViewSet, basename="article")
router.register("comments", CommentViewSet, basename="comment")
router.register("audit-logs", AuditLogViewSet, basename="audit-log")

engine = create_async_engine("sqlite+aiosqlite:///./advanced.db")
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

app = FastAPI(title="Advanced FastREST API", version="1.0.0")

# Full app configuration — Django-style settings
configure(app, {
    # Agent integration
    "SKILL_NAME": "advanced-api",
    "SKILL_BASE_URL": "http://localhost:8000/api",
    "SKILL_DESCRIPTION": "An article CMS API with authentication, scoped permissions, and rate limiting.",
    "SKILL_AUTH_DESCRIPTION": "Use Bearer token: admin-secret (admin), editor-secret (editor), viewer-secret (viewer).",
    "SKILL_INCLUDE_EXAMPLES": True,
    "SKILL_MAX_EXAMPLES_PER_RESOURCE": 3,

    # MCP
    "MCP_ENABLED": True,
    "MCP_PREFIX": "/mcp",

    # Defaults (can be overridden per-viewset)
    "DEFAULT_AUTHENTICATION_CLASSES": [token_auth],
    "DEFAULT_PERMISSION_CLASSES": [IsAuthenticatedOrReadOnly],
})

app.include_router(router.urls, prefix="/api")
mount_mcp(app, router)


@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


viewsets = [ArticleViewSet, CommentViewSet, AuditLogViewSet]

@app.middleware("http")
async def db_session(request: Request, call_next):
    async with SessionLocal() as session:
        async with session.begin():
            originals = {}
            for vs in viewsets:
                originals[vs] = vs.__init__
                def make_patched(original):
                    def patched_init(self, **kwargs):
                        original(self, **kwargs)
                        self._session = session
                    return patched_init
                vs.__init__ = make_patched(originals[vs])
            try:
                response = await call_next(request)
            finally:
                for vs in viewsets:
                    vs.__init__ = originals[vs]
            return response
