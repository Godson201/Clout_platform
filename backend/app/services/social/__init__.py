from app.core.config import get_settings
from app.models.enums import SocialPlatform
from app.services.social.base import SocialPlatformAdapter
from app.services.social.meta import FacebookAdapter, InstagramAdapter
from app.services.social.mock import MockSocialAdapter
from app.services.social.tiktok import TikTokAdapter
from app.services.social.youtube import YouTubeAdapter

__all__ = ["SocialPlatformAdapter", "get_adapter"]

_real_adapters: dict[SocialPlatform, SocialPlatformAdapter] = {
    SocialPlatform.TIKTOK: TikTokAdapter(),
    SocialPlatform.INSTAGRAM: InstagramAdapter(),
    SocialPlatform.FACEBOOK: FacebookAdapter(),
    SocialPlatform.YOUTUBE: YouTubeAdapter(),
}


def _platform_is_configured(platform: SocialPlatform, settings) -> bool:
    """SOCIAL_OAUTH_MODE=live is an "enable real mode where it's actually
    configured" switch, not all-or-nothing — a brand connecting Instagram
    shouldn't be blocked on TikTok/YouTube credentials that don't exist yet,
    and vice versa. Platforms without credentials fall back to the mock
    adapter, which already labels itself "(simulated)" on the consent page,
    so this never silently pretends to be a real connection.
    """
    if platform in (SocialPlatform.INSTAGRAM, SocialPlatform.FACEBOOK):
        return bool(settings.META_APP_ID and settings.META_APP_SECRET)
    if platform == SocialPlatform.TIKTOK:
        return bool(settings.TIKTOK_CLIENT_KEY and settings.TIKTOK_CLIENT_SECRET)
    if platform == SocialPlatform.YOUTUBE:
        return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
    return False


def get_adapter(platform: SocialPlatform) -> SocialPlatformAdapter:
    settings = get_settings()
    if settings.SOCIAL_OAUTH_MODE == "live" and _platform_is_configured(platform, settings):
        return _real_adapters[platform]
    return MockSocialAdapter(platform)
