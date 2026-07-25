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

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
COMMENT_THREADS_URL = "https://www.googleapis.com/youtube/v3/commentThreads"

# youtube.upload requires the OAuth consent screen to pass Google's verification
# for production use once past 100 test users — see PLATFORM_CAPABILITIES.
SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"


class YouTubeConfigurationError(RuntimeError):
    pass


def _require(value: str | None, name: str) -> str:
    if not value:
        raise YouTubeConfigurationError(f"{name} is not configured — set it to use YouTube live")
    return value


class YouTubeAdapter:
    """Real Google OAuth2 + YouTube Data API v3 client. Never exercised in this
    codebase's tests — no sandbox app credentials exist in this environment.
    """

    platform = SocialPlatform.YOUTUBE

    def build_authorization_url(self, *, state: str, redirect_uri: str) -> AuthorizationRequest:
        client_id = _require(settings.GOOGLE_CLIENT_ID, "GOOGLE_CLIENT_ID")
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": SCOPES,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return AuthorizationRequest(authorization_url=f"{AUTH_URL}?{urlencode(params)}")

    async def exchange_code_for_token(
        self, *, code: str, redirect_uri: str, code_verifier: str | None
    ) -> OAuthTokenResult:
        client_id = _require(settings.GOOGLE_CLIENT_ID, "GOOGLE_CLIENT_ID")
        client_secret = _require(settings.GOOGLE_CLIENT_SECRET, "GOOGLE_CLIENT_SECRET")

        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(
                TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )
            token_resp.raise_for_status()
            token_body = token_resp.json()

            channel_resp = await client.get(
                f"{VIDEOS_URL.rsplit('/', 1)[0]}/channels",
                params={"part": "id,snippet", "mine": "true"},
                headers={"Authorization": f"Bearer {token_body['access_token']}"},
            )
            channel_resp.raise_for_status()
            channels = channel_resp.json().get("items", [])

        channel = channels[0] if channels else {}
        return OAuthTokenResult(
            access_token=token_body["access_token"],
            refresh_token=token_body.get("refresh_token"),
            expires_in_seconds=token_body.get("expires_in"),
            external_account_id=channel.get("id", ""),
            handle=channel.get("snippet", {}).get("title", ""),
            scopes=token_body.get("scope", "").split(" "),
        )

    async def refresh_access_token(self, refresh_token: str) -> OAuthTokenResult:
        client_id = _require(settings.GOOGLE_CLIENT_ID, "GOOGLE_CLIENT_ID")
        client_secret = _require(settings.GOOGLE_CLIENT_SECRET, "GOOGLE_CLIENT_SECRET")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            resp.raise_for_status()
            body = resp.json()

        return OAuthTokenResult(
            access_token=body["access_token"],
            refresh_token=refresh_token,  # Google doesn't rotate refresh tokens by default
            expires_in_seconds=body.get("expires_in"),
            external_account_id="",
            handle="",
            scopes=body.get("scope", "").split(" "),
        )

    async def publish_post(self, *, access_token: str, video_url: str, caption: str) -> PublishResult:
        # Real uploads use the resumable upload protocol (initiate, then PUT the
        # video bytes in chunks); simplified here to fetching the already-processed
        # rendition and sending it in one multipart request, which the API also
        # accepts for files under its non-resumable size threshold.
        async with httpx.AsyncClient(timeout=60.0) as client:
            video_bytes_resp = await client.get(video_url)
            video_bytes_resp.raise_for_status()

            upload_resp = await client.post(
                UPLOAD_URL,
                params={"uploadType": "multipart", "part": "snippet,status"},
                headers={"Authorization": f"Bearer {access_token}"},
                files={
                    "metadata": (
                        None,
                        (
                            '{"snippet":{"title":"CLOUT campaign short","description":"'
                            + caption.replace('"', "'")
                            + '"},"status":{"privacyStatus":"public"}}'
                        ),
                        "application/json",
                    ),
                    "video": ("video.mp4", video_bytes_resp.content, "video/mp4"),
                },
            )
            upload_resp.raise_for_status()
            video_id = upload_resp.json()["id"]

        return PublishResult(external_post_id=video_id, post_url=f"https://www.youtube.com/shorts/{video_id}")

    async def fetch_metrics(self, *, access_token: str, external_post_id: str) -> MetricsResult:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                VIDEOS_URL,
                params={"part": "statistics", "id": external_post_id},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])

        if not items:
            return MetricsResult(views=0, likes=0, comments=0, shares=None, post_exists=False)

        stats = items[0]["statistics"]
        return MetricsResult(
            views=int(stats.get("viewCount", 0)),
            likes=int(stats.get("likeCount", 0)),
            comments=int(stats.get("commentCount", 0)),
            shares=None,  # YouTube Data API doesn't expose a share count
            post_exists=True,
        )

    async def fetch_comments(
        self, *, access_token: str, external_post_id: str, since: datetime | None
    ) -> list[CommentResult]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                COMMENT_THREADS_URL,
                params={"part": "snippet", "videoId": external_post_id, "maxResults": 100},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])

        results = []
        for item in items:
            top = item["snippet"]["topLevelComment"]["snippet"]
            posted_at = None
            if top.get("publishedAt"):
                posted_at = datetime.fromisoformat(top["publishedAt"].replace("Z", "+00:00")).astimezone(timezone.utc)
            results.append(
                CommentResult(
                    external_comment_id=item["snippet"]["topLevelComment"]["id"],
                    author_handle=top.get("authorDisplayName", ""),
                    text=top.get("textDisplay", ""),
                    posted_at=posted_at,
                )
            )

        if since is None:
            return results
        return [c for c in results if c.posted_at is not None and c.posted_at > since]
