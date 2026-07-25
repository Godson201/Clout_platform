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


def get_adapter(platform: SocialPlatform) -> SocialPlatformAdapter:
    settings = get_settings()
    if settings.SOCIAL_OAUTH_MODE == "live":
        return _real_adapters[platform]
    return MockSocialAdapter(platform)
