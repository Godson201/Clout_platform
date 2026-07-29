from app.core.config import get_settings
from app.models.enums import SocialPlatform
from app.services.social import get_adapter
from app.services.social.meta import InstagramAdapter
from app.services.social.mock import MockSocialAdapter


class TestPerPlatformAdapterSelection:
    """SOCIAL_OAUTH_MODE=live is an "enable where configured" switch, not
    all-or-nothing — connecting one platform's real credentials must never
    require every other platform to have credentials too, or break them.
    """

    def test_mock_mode_never_returns_a_real_adapter(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "SOCIAL_OAUTH_MODE", "mock")
        monkeypatch.setattr(settings, "META_APP_ID", "test-app-id")
        monkeypatch.setattr(settings, "META_APP_SECRET", "test-secret")

        adapter = get_adapter(SocialPlatform.INSTAGRAM)
        assert isinstance(adapter, MockSocialAdapter)

    def test_live_mode_with_credentials_returns_real_adapter(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "SOCIAL_OAUTH_MODE", "live")
        monkeypatch.setattr(settings, "META_APP_ID", "test-app-id")
        monkeypatch.setattr(settings, "META_APP_SECRET", "test-secret")

        adapter = get_adapter(SocialPlatform.INSTAGRAM)
        assert isinstance(adapter, InstagramAdapter)

    def test_live_mode_without_credentials_falls_back_to_mock(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "SOCIAL_OAUTH_MODE", "live")
        monkeypatch.setattr(settings, "META_APP_ID", None)
        monkeypatch.setattr(settings, "META_APP_SECRET", None)

        adapter = get_adapter(SocialPlatform.INSTAGRAM)
        assert isinstance(adapter, MockSocialAdapter)

    def test_configuring_one_platform_does_not_affect_another(self, monkeypatch):
        settings = get_settings()
        monkeypatch.setattr(settings, "SOCIAL_OAUTH_MODE", "live")
        monkeypatch.setattr(settings, "META_APP_ID", "test-app-id")
        monkeypatch.setattr(settings, "META_APP_SECRET", "test-secret")
        monkeypatch.setattr(settings, "TIKTOK_CLIENT_KEY", None)
        monkeypatch.setattr(settings, "TIKTOK_CLIENT_SECRET", None)

        instagram_adapter = get_adapter(SocialPlatform.INSTAGRAM)
        tiktok_adapter = get_adapter(SocialPlatform.TIKTOK)

        assert isinstance(instagram_adapter, InstagramAdapter)
        assert isinstance(tiktok_adapter, MockSocialAdapter)
