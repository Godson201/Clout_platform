import base64
import hashlib
import secrets
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

AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
PUBLISH_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
VIDEO_QUERY_URL = "https://open.tiktokapis.com/v2/video/query/"
COMMENT_LIST_URL = "https://open.tiktokapis.com/v2/video/comment/list/"

# Content Posting API access (video.publish) is separately audited by TikTok on
# top of basic OAuth app approval — see PLATFORM_CAPABILITIES for why
# can_auto_publish stays False until that's actually been granted.
SCOPES = "user.info.basic,video.publish,video.list"


class TikTokConfigurationError(RuntimeError):
    pass


def _require(value: str | None, name: str) -> str:
    if not value:
        raise TikTokConfigurationError(f"{name} is not configured — set it to use TikTok live")
    return value


class TikTokAdapter:
    """Real TikTok v2 OAuth + Content Posting/Display API client. Never
    exercised in this codebase's tests — no sandbox app credentials exist in
    this environment — but implements the actual API shape (including PKCE,
    which TikTok's v2 OAuth requires) so flipping SOCIAL_OAUTH_MODE to "live"
    plus filling in TIKTOK_CLIENT_KEY/SECRET is the entire migration.
    """

    platform = SocialPlatform.TIKTOK

    def build_authorization_url(self, *, state: str, redirect_uri: str) -> AuthorizationRequest:
        client_key = _require(settings.TIKTOK_CLIENT_KEY, "TIKTOK_CLIENT_KEY")
        code_verifier = secrets.token_urlsafe(64)[:128]
        code_challenge = base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest()).decode().rstrip("=")

        params = {
            "client_key": client_key,
            "scope": SCOPES,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return AuthorizationRequest(authorization_url=f"{AUTH_URL}?{urlencode(params)}", code_verifier=code_verifier)

    async def exchange_code_for_token(
        self, *, code: str, redirect_uri: str, code_verifier: str | None
    ) -> OAuthTokenResult:
        client_key = _require(settings.TIKTOK_CLIENT_KEY, "TIKTOK_CLIENT_KEY")
        client_secret = _require(settings.TIKTOK_CLIENT_SECRET, "TIKTOK_CLIENT_SECRET")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                TOKEN_URL,
                data={
                    "client_key": client_key,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                    "code_verifier": code_verifier,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            body = resp.json()

        return OAuthTokenResult(
            access_token=body["access_token"],
            refresh_token=body.get("refresh_token"),
            expires_in_seconds=body.get("expires_in"),
            external_account_id=body["open_id"],
            handle=body.get("open_id", ""),
            scopes=body.get("scope", "").split(","),
        )

    async def refresh_access_token(self, refresh_token: str) -> OAuthTokenResult:
        client_key = _require(settings.TIKTOK_CLIENT_KEY, "TIKTOK_CLIENT_KEY")
        client_secret = _require(settings.TIKTOK_CLIENT_SECRET, "TIKTOK_CLIENT_SECRET")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                TOKEN_URL,
                data={
                    "client_key": client_key,
                    "client_secret": client_secret,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
            )
            resp.raise_for_status()
            body = resp.json()

        return OAuthTokenResult(
            access_token=body["access_token"],
            refresh_token=body.get("refresh_token", refresh_token),
            expires_in_seconds=body.get("expires_in"),
            external_account_id=body["open_id"],
            handle=body.get("open_id", ""),
            scopes=body.get("scope", "").split(","),
        )

    async def publish_post(self, *, access_token: str, video_url: str, caption: str) -> PublishResult:
        # Real Content Posting API is a multi-step init/upload/status flow;
        # PULL_FROM_URL source (rather than chunked upload) works when the video
        # is already hosted at a stable URL, which storage.py's S3/media URLs are.
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                PUBLISH_INIT_URL,
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json={
                    "post_info": {"title": caption, "privacy_level": "PUBLIC_TO_EVERYONE"},
                    "source_info": {"source": "PULL_FROM_URL", "video_url": video_url},
                },
            )
            resp.raise_for_status()
            body = resp.json()

        publish_id = body["data"]["publish_id"]
        return PublishResult(external_post_id=publish_id, post_url=f"https://www.tiktok.com/publish/{publish_id}")

    async def fetch_metrics(self, *, access_token: str, external_post_id: str) -> MetricsResult:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                VIDEO_QUERY_URL,
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                params={"fields": "id,view_count,like_count,comment_count,share_count"},
                json={"filters": {"video_ids": [external_post_id]}},
            )
            resp.raise_for_status()
            body = resp.json()

        videos = body.get("data", {}).get("videos", [])
        if not videos:
            return MetricsResult(views=0, likes=0, comments=0, shares=0, post_exists=False)

        video = videos[0]
        return MetricsResult(
            views=video.get("view_count", 0),
            likes=video.get("like_count", 0),
            comments=video.get("comment_count", 0),
            shares=video.get("share_count", 0),
            post_exists=True,
        )

    async def fetch_comments(
        self, *, access_token: str, external_post_id: str, since: datetime | None
    ) -> list[CommentResult]:
        # Comment Management is a separately-scoped, separately-audited part of
        # the Content Posting API on top of basic publish access — see
        # PLATFORM_CAPABILITIES.can_fetch_comments.
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                COMMENT_LIST_URL,
                headers={"Authorization": f"Bearer {access_token}"},
                params={"video_id": external_post_id, "fields": "id,text,create_time,user"},
            )
            resp.raise_for_status()
            body = resp.json()

        results = [
            CommentResult(
                external_comment_id=str(c["id"]),
                author_handle=c.get("user", {}).get("display_name", ""),
                text=c.get("text", ""),
                posted_at=(
                    datetime.fromtimestamp(c["create_time"], tz=timezone.utc) if c.get("create_time") else None
                ),
            )
            for c in body.get("data", {}).get("comments", [])
        ]
        if since is None:
            return results
        return [c for c in results if c.posted_at is not None and c.posted_at > since]
