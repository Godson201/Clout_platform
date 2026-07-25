from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.models.enums import SocialPlatform


@dataclass(frozen=True)
class AuthorizationRequest:
    authorization_url: str
    # TikTok's v2 OAuth requires PKCE; other platforms don't use this (None).
    # Stored server-side against the pending SocialOAuthState row, never sent
    # to the client — only the resulting code_challenge goes into the URL.
    code_verifier: str | None = None


@dataclass(frozen=True)
class OAuthTokenResult:
    access_token: str
    refresh_token: str | None
    expires_in_seconds: int | None
    external_account_id: str
    handle: str
    scopes: list[str]


@dataclass(frozen=True)
class PublishResult:
    external_post_id: str
    post_url: str


@dataclass(frozen=True)
class MetricsResult:
    views: int
    likes: int
    comments: int
    shares: int | None
    post_exists: bool


@dataclass(frozen=True)
class CommentResult:
    external_comment_id: str
    author_handle: str
    text: str
    posted_at: datetime | None


class SocialPlatformAdapter(Protocol):
    """One implementation per platform, covering OAuth + publishing + metrics.
    Adapters implement the mechanics unconditionally — whether they're actually
    *called* for publishing/metrics is a decision the service layer makes by
    consulting app.core.platform_capabilities.PLATFORM_CAPABILITIES, not
    something an adapter decides about itself. This keeps "can we do X on this
    platform right now" in exactly one place, checkable without touching adapter
    code, and flippable per-platform the moment real API access is granted.
    """

    platform: SocialPlatform

    def build_authorization_url(self, *, state: str, redirect_uri: str) -> AuthorizationRequest: ...

    async def exchange_code_for_token(
        self, *, code: str, redirect_uri: str, code_verifier: str | None
    ) -> OAuthTokenResult: ...

    async def refresh_access_token(self, refresh_token: str) -> OAuthTokenResult: ...

    async def publish_post(self, *, access_token: str, video_url: str, caption: str) -> PublishResult: ...

    async def fetch_metrics(self, *, access_token: str, external_post_id: str) -> MetricsResult: ...

    async def fetch_comments(
        self, *, access_token: str, external_post_id: str, since: datetime | None
    ) -> list[CommentResult]: ...
