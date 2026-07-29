from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx

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

GRAPH_VERSION = "v19.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"
AUTH_URL = f"https://www.facebook.com/{GRAPH_VERSION}/dialog/oauth"

FACEBOOK_SCOPES = "pages_show_list,pages_manage_posts,pages_read_engagement"


class MetaConfigurationError(RuntimeError):
    pass


def _require(value: str | None, name: str) -> str:
    if not value:
        raise MetaConfigurationError(f"{name} is not configured — set it to use Meta (Facebook) live")
    return value


class _MetaOAuthBase:
    """Classic Facebook Login-based Meta Graph API OAuth. Instagram used to
    share this (see git history) but now goes through the standalone
    "Instagram API with Instagram Login" product instead — its own app
    credentials, its own OAuth host — see services/social/instagram_login.py.
    Kept as a base class rather than folded into FacebookAdapter directly in
    case another classic-Facebook-Login Meta product joins it later.
    """

    scopes: str

    def build_authorization_url(self, *, state: str, redirect_uri: str) -> AuthorizationRequest:
        app_id = _require(settings.META_APP_ID, "META_APP_ID")
        params = {"client_id": app_id, "redirect_uri": redirect_uri, "state": state, "scope": self.scopes}
        return AuthorizationRequest(authorization_url=f"{AUTH_URL}?{urlencode(params)}")

    async def exchange_code_for_token(
        self, *, code: str, redirect_uri: str, code_verifier: str | None
    ) -> OAuthTokenResult:
        app_id = _require(settings.META_APP_ID, "META_APP_ID")
        app_secret = _require(settings.META_APP_SECRET, "META_APP_SECRET")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GRAPH_BASE}/oauth/access_token",
                params={"client_id": app_id, "redirect_uri": redirect_uri, "client_secret": app_secret, "code": code},
            )
            resp.raise_for_status()
            token_body = resp.json()

            # Meta tokens are tied to the user; publishing happens against a Page/IG
            # Business Account the user manages — resolve that as "the account".
            me_resp = await client.get(
                f"{GRAPH_BASE}/me/accounts", params={"access_token": token_body["access_token"]}
            )
            me_resp.raise_for_status()
            pages = me_resp.json().get("data", [])

        page = pages[0] if pages else {}
        return OAuthTokenResult(
            access_token=token_body["access_token"],
            refresh_token=None,  # Meta uses long-lived token exchange/refresh, not a refresh_token grant
            expires_in_seconds=token_body.get("expires_in"),
            external_account_id=page.get("id", ""),
            handle=page.get("name", ""),
            scopes=self.scopes.split(","),
        )

    async def refresh_access_token(self, refresh_token: str) -> OAuthTokenResult:
        # Meta's equivalent of refresh is exchanging a short-lived token for a
        # long-lived one via a GET with fb_exchange_token — there's no rotating
        # refresh_token grant like TikTok/Google. `refresh_token` here is
        # actually the previous access_token, passed in for exchange.
        app_id = _require(settings.META_APP_ID, "META_APP_ID")
        app_secret = _require(settings.META_APP_SECRET, "META_APP_SECRET")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GRAPH_BASE}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": app_id,
                    "client_secret": app_secret,
                    "fb_exchange_token": refresh_token,
                },
            )
            resp.raise_for_status()
            body = resp.json()

        return OAuthTokenResult(
            access_token=body["access_token"],
            refresh_token=None,
            expires_in_seconds=body.get("expires_in"),
            external_account_id="",
            handle="",
            scopes=self.scopes.split(","),
        )

    async def _fetch_graph_comments(
        self, *, access_token: str, external_post_id: str, since: datetime | None
    ) -> list[CommentResult]:
        # Same /{id}/comments shape for both Instagram media and Facebook posts.
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GRAPH_BASE}/{external_post_id}/comments",
                params={"fields": "id,from,text,timestamp", "access_token": access_token},
            )
            resp.raise_for_status()
            body = resp.json()

        results = []
        for c in body.get("data", []):
            posted_at = None
            if c.get("timestamp"):
                posted_at = datetime.fromisoformat(c["timestamp"].replace("Z", "+00:00")).astimezone(timezone.utc)
            results.append(
                CommentResult(
                    external_comment_id=c["id"],
                    author_handle=c.get("from", {}).get("username", c.get("from", {}).get("name", "")),
                    text=c.get("text", ""),
                    posted_at=posted_at,
                )
            )

        if since is None:
            return results
        return [c for c in results if c.posted_at is not None and c.posted_at > since]


class FacebookAdapter(_MetaOAuthBase):
    platform = SocialPlatform.FACEBOOK
    scopes = FACEBOOK_SCOPES

    async def publish_post(self, *, access_token: str, video_url: str, caption: str) -> PublishResult:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{GRAPH_BASE}/me/videos",
                data={"file_url": video_url, "description": caption, "access_token": access_token},
            )
            resp.raise_for_status()
            post_id = resp.json()["id"]

        return PublishResult(external_post_id=post_id, post_url=f"https://www.facebook.com/watch/?v={post_id}")

    async def fetch_metrics(self, *, access_token: str, external_post_id: str) -> MetricsResult:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GRAPH_BASE}/{external_post_id}",
                params={
                    "fields": "views,likes.summary(true),comments.summary(true),shares",
                    "access_token": access_token,
                },
            )
            if resp.status_code == 404:
                return MetricsResult(views=0, likes=0, comments=0, shares=0, post_exists=False)
            resp.raise_for_status()
            body = resp.json()

        return MetricsResult(
            views=body.get("views", 0),
            likes=body.get("likes", {}).get("summary", {}).get("total_count", 0),
            comments=body.get("comments", {}).get("summary", {}).get("total_count", 0),
            shares=body.get("shares", {}).get("count", 0),
            post_exists=True,
        )

    async def fetch_comments(
        self, *, access_token: str, external_post_id: str, since: datetime | None
    ) -> list[CommentResult]:
        return await self._fetch_graph_comments(access_token=access_token, external_post_id=external_post_id, since=since)
