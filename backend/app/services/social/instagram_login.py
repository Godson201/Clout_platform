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

# "Instagram API with Instagram Login" — Meta's newer standalone Instagram
# product (separate app credentials, distinct from the classic Facebook Login
# flow in meta.py). The Instagram professional account authenticates directly
# against instagram.com rather than through a linked Facebook Page, so every
# endpoint here lives on api.instagram.com/graph.instagram.com, never
# graph.facebook.com. See CLOUT's product-comparison note in the PR/commit
# that added this file for why two adapters exist for "one platform."
GRAPH_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.instagram.com/{GRAPH_VERSION}"
AUTH_URL = "https://www.instagram.com/oauth/authorize"
SHORT_LIVED_TOKEN_URL = "https://api.instagram.com/oauth/access_token"

# instagram_business_content_publish only works for an Instagram Business/
# Creator account, and requires Meta App Review before it works for anyone
# other than the app's own added testers — see app.core.platform_capabilities.
SCOPES = "instagram_business_basic,instagram_business_content_publish,instagram_business_manage_comments"


class InstagramLoginConfigurationError(RuntimeError):
    pass


def _require(value: str | None, name: str) -> str:
    if not value:
        raise InstagramLoginConfigurationError(f"{name} is not configured — set it to use Instagram Login live")
    return value


class InstagramLoginAdapter:
    platform = SocialPlatform.INSTAGRAM

    def build_authorization_url(self, *, state: str, redirect_uri: str) -> AuthorizationRequest:
        app_id = _require(settings.INSTAGRAM_APP_ID, "INSTAGRAM_APP_ID")
        params = {
            "client_id": app_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": SCOPES,
            "state": state,
        }
        return AuthorizationRequest(authorization_url=f"{AUTH_URL}?{urlencode(params)}")

    async def exchange_code_for_token(
        self, *, code: str, redirect_uri: str, code_verifier: str | None
    ) -> OAuthTokenResult:
        app_id = _require(settings.INSTAGRAM_APP_ID, "INSTAGRAM_APP_ID")
        app_secret = _require(settings.INSTAGRAM_APP_SECRET, "INSTAGRAM_APP_SECRET")

        async with httpx.AsyncClient(timeout=15.0) as client:
            # Step 1: short-lived token (~1 hour), form-encoded POST per Meta's spec.
            short_resp = await client.post(
                SHORT_LIVED_TOKEN_URL,
                data={
                    "client_id": app_id,
                    "client_secret": app_secret,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
            )
            short_resp.raise_for_status()
            short_body = short_resp.json()
            # Some Meta API versions wrap this in {"data": [...]}, others return
            # the object directly — handle both rather than guess wrong.
            if "data" in short_body:
                short_body = short_body["data"][0]
            short_lived_token = short_body["access_token"]
            ig_user_id = str(short_body["user_id"])

            # Step 2: exchange for a 60-day long-lived token — this is the token
            # actually stored (see services/social_accounts.py), never the
            # short-lived one, so metrics/publishing keep working for weeks.
            long_resp = await client.get(
                f"{GRAPH_BASE}/access_token",
                params={
                    "grant_type": "ig_exchange_token",
                    "client_secret": app_secret,
                    "access_token": short_lived_token,
                },
            )
            long_resp.raise_for_status()
            long_body = long_resp.json()

            me_resp = await client.get(
                f"{GRAPH_BASE}/{ig_user_id}", params={"fields": "username", "access_token": long_body["access_token"]}
            )
            me_resp.raise_for_status()
            handle = me_resp.json().get("username", "")

        return OAuthTokenResult(
            access_token=long_body["access_token"],
            refresh_token=None,  # refreshed via refresh_access_token below, not a rotating grant
            expires_in_seconds=long_body.get("expires_in"),
            external_account_id=ig_user_id,
            handle=handle,
            scopes=SCOPES.split(","),
        )

    async def refresh_access_token(self, refresh_token: str) -> OAuthTokenResult:
        # `refresh_token` here is actually the previous long-lived access_token —
        # Instagram Login has no rotating refresh_token grant, only in-place
        # long-lived-token refresh (valid once the token is at least 24h old).
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GRAPH_BASE}/refresh_access_token",
                params={"grant_type": "ig_refresh_token", "access_token": refresh_token},
            )
            resp.raise_for_status()
            body = resp.json()

        return OAuthTokenResult(
            access_token=body["access_token"],
            refresh_token=None,
            expires_in_seconds=body.get("expires_in"),
            external_account_id="",
            handle="",
            scopes=SCOPES.split(","),
        )

    async def publish_post(self, *, access_token: str, video_url: str, caption: str) -> PublishResult:
        # external_account_id (the IG-scoped user id captured at OAuth time) is
        # threaded through by the caller as part of the SocialAccount, not this
        # signature — see services/social_posting.py, matching the Meta adapter's
        # existing convention of publishing against "me" and letting the token
        # itself scope which account that resolves to.
        async with httpx.AsyncClient(timeout=30.0) as client:
            container_resp = await client.post(
                f"{GRAPH_BASE}/me/media",
                data={"video_url": video_url, "caption": caption, "media_type": "REELS", "access_token": access_token},
            )
            container_resp.raise_for_status()
            creation_id = container_resp.json()["id"]

            publish_resp = await client.post(
                f"{GRAPH_BASE}/me/media_publish", data={"creation_id": creation_id, "access_token": access_token}
            )
            publish_resp.raise_for_status()
            media_id = publish_resp.json()["id"]

        return PublishResult(external_post_id=media_id, post_url=f"https://www.instagram.com/reel/{media_id}/")

    async def fetch_metrics(self, *, access_token: str, external_post_id: str) -> MetricsResult:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GRAPH_BASE}/{external_post_id}/insights",
                params={"metric": "plays,likes,comments,shares", "access_token": access_token},
            )
            if resp.status_code == 404:
                return MetricsResult(views=0, likes=0, comments=0, shares=0, post_exists=False)
            resp.raise_for_status()
            values = {row["name"]: row["values"][0]["value"] for row in resp.json().get("data", [])}

        return MetricsResult(
            views=values.get("plays", 0),
            likes=values.get("likes", 0),
            comments=values.get("comments", 0),
            shares=values.get("shares", 0),
            post_exists=True,
        )

    async def fetch_comments(
        self, *, access_token: str, external_post_id: str, since: datetime | None
    ) -> list[CommentResult]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{GRAPH_BASE}/{external_post_id}/comments",
                params={"fields": "id,username,text,timestamp", "access_token": access_token},
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
                    author_handle=c.get("username", ""),
                    text=c.get("text", ""),
                    posted_at=posted_at,
                )
            )

        if since is None:
            return results
        return [c for c in results if c.posted_at is not None and c.posted_at > since]
