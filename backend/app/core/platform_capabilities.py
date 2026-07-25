from dataclasses import dataclass

from app.core.config import get_settings
from app.models.enums import SocialPlatform


@dataclass(frozen=True)
class PlatformCapabilities:
    """What CLOUT can actually do on a platform *right now*, independent of
    whether the adapter code exists. All four flags default to False across
    every platform below — per the confirmed business decision, every adapter
    ships in manual/assisted mode and gets flipped on independently once that
    platform's app has actually been granted the relevant API access (business/
    creator account verification, Meta App Review, TikTok's audited Content
    Posting API access, YouTube's OAuth consent screen verification, etc.).
    Flipping a flag here is the entire activation step — no call-site changes,
    since services/social_posting.py and social_metrics.py already branch on
    these flags rather than assuming uniform capability.
    """

    can_auto_publish: bool
    can_schedule: bool
    can_fetch_metrics: bool
    can_fetch_comments: bool


PLATFORM_CAPABILITIES: dict[SocialPlatform, PlatformCapabilities] = {
    SocialPlatform.TIKTOK: PlatformCapabilities(
        can_auto_publish=False, can_schedule=False, can_fetch_metrics=False, can_fetch_comments=False
    ),
    SocialPlatform.INSTAGRAM: PlatformCapabilities(
        can_auto_publish=False, can_schedule=False, can_fetch_metrics=False, can_fetch_comments=False
    ),
    SocialPlatform.FACEBOOK: PlatformCapabilities(
        can_auto_publish=False, can_schedule=False, can_fetch_metrics=False, can_fetch_comments=False
    ),
    SocialPlatform.YOUTUBE: PlatformCapabilities(
        can_auto_publish=False, can_schedule=False, can_fetch_metrics=False, can_fetch_comments=False
    ),
}

_MOCK_CAPABILITIES = PlatformCapabilities(
    can_auto_publish=True, can_schedule=True, can_fetch_metrics=True, can_fetch_comments=True
)


def get_capabilities(platform: SocialPlatform) -> PlatformCapabilities:
    """What services/social_posting.py and social_metrics.py actually check —
    never PLATFORM_CAPABILITIES directly. In mock mode (local dev, the default
    test suite) this claims full capability on every platform so the whole
    auto-publish + metrics pipeline is exercised end-to-end by default, the
    same way Phase 4's MockPaymentClient always resolves successfully unless a
    test deliberately asks it not to. In live mode it returns the honest,
    currently-all-False matrix above, which is what makes production fall back
    to the manual/assisted flow today.
    """
    settings = get_settings()
    if settings.SOCIAL_OAUTH_MODE == "mock":
        return _MOCK_CAPABILITIES
    return PLATFORM_CAPABILITIES[platform]
