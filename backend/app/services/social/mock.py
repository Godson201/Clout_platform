import uuid
from datetime import datetime, timedelta, timezone

from app.core.config import get_settings
from app.models.enums import SocialPlatform
from app.services.social.base import (
    AuthorizationRequest,
    CommentResult,
    MetricsResult,
    OAuthTokenResult,
    PublishResult,
)

settings = get_settings()

# Module-level so repeated polls of the same post show real growth instead of a
# flat line — mirrors the growth a real post's view count shows between polls.
_metrics_poll_counts: dict[str, int] = {}
_comment_poll_counts: dict[str, int] = {}

# Deliberately spans every CommentCategory the rule-based classifier
# recognizes (question / suggestion / complaint / positive / negative /
# neutral) so tests exercising the mock pipeline exercise every category
# without needing to hand-craft comment text per test.
_COMMENT_TEMPLATES = [
    "How much does this cost?",
    "Can you ship this internationally?",
    "You should add a discount code for loyal fans",
    "This is amazing, I love it!!",
    "Best product I've tried this year, highly recommend",
    "This is a scam, I want my money back",
    "Terrible experience, very disappointed with the quality",
    "meh, it's okay I guess",
]

_COMMENT_EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)


class MockSocialAdapter:
    """Stands in for every platform's real OAuth/publish/metrics/comments APIs
    — used whenever SOCIAL_OAUTH_MODE=mock (local dev, the whole test suite;
    there are no real app credentials for any platform in this environment).
    Everything here is deterministic and derived only from its own inputs, so
    it needs no setup beyond instantiation.
    """

    def __init__(self, platform: SocialPlatform):
        self.platform = platform

    def build_authorization_url(self, *, state: str, redirect_uri: str) -> AuthorizationRequest:
        # Points at our own frontend's mock consent page rather than a fake
        # external domain, so clicking "Connect" in mock mode is actually
        # clickable end-to-end in a browser (simulates "you're on TikTok's
        # consent screen, click Approve") instead of a dead link — the redirect
        # shape (browser leaves our app, comes back with ?code&state) is
        # otherwise identical to what a real provider does.
        code = f"mock-code-{state}"
        url = (
            f"{settings.FRONTEND_BASE_URL}/social/mock-consent/{self.platform.value}"
            f"?state={state}&redirect_uri={redirect_uri}&code={code}"
        )
        return AuthorizationRequest(authorization_url=url, code_verifier=f"mock-verifier-{state}")

    async def exchange_code_for_token(
        self, *, code: str, redirect_uri: str, code_verifier: str | None
    ) -> OAuthTokenResult:
        return OAuthTokenResult(
            access_token=f"mock-access-{code}",
            refresh_token=f"mock-refresh-{code}",
            expires_in_seconds=3600,
            external_account_id=f"mock-ext-{code}",
            handle=f"mockuser-{self.platform.value}",
            scopes=["mock.read", "mock.publish"],
        )

    async def refresh_access_token(self, refresh_token: str) -> OAuthTokenResult:
        return OAuthTokenResult(
            access_token=f"mock-access-refreshed-{refresh_token}",
            refresh_token=refresh_token,
            expires_in_seconds=3600,
            external_account_id=f"mock-ext-{refresh_token}",
            handle=f"mockuser-{self.platform.value}",
            scopes=["mock.read", "mock.publish"],
        )

    async def publish_post(self, *, access_token: str, video_url: str, caption: str) -> PublishResult:
        post_id = str(uuid.uuid4())
        return PublishResult(
            external_post_id=post_id, post_url=f"https://mock.social/{self.platform.value}/posts/{post_id}"
        )

    async def fetch_metrics(self, *, access_token: str, external_post_id: str) -> MetricsResult:
        count = _metrics_poll_counts[external_post_id] = _metrics_poll_counts.get(external_post_id, 0) + 1
        return MetricsResult(
            views=count * 500, likes=count * 40, comments=count * 5, shares=count * 2, post_exists=True
        )

    async def fetch_comments(
        self, *, access_token: str, external_post_id: str, since: datetime | None
    ) -> list[CommentResult]:
        # Reveals one more comment from the fixed pool per poll (capped at the
        # pool size) so incremental (`since`-filtered) polling has something
        # real to exercise, the same growth-per-poll idea fetch_metrics uses.
        count = _comment_poll_counts[external_post_id] = _comment_poll_counts.get(external_post_id, 0) + 1
        revealed = min(count, len(_COMMENT_TEMPLATES))

        all_comments = [
            CommentResult(
                external_comment_id=f"{external_post_id}-comment-{i}",
                author_handle=f"mockfan{i}",
                text=_COMMENT_TEMPLATES[i],
                posted_at=_COMMENT_EPOCH + timedelta(minutes=i),
            )
            for i in range(revealed)
        ]
        if since is None:
            return all_comments
        return [c for c in all_comments if c.posted_at is not None and c.posted_at > since]
