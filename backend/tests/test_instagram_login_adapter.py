import pytest

from app.services.social.instagram_login import InstagramLoginAdapter, InstagramLoginConfigurationError


class TestInstagramLoginAuthorizationUrl:
    def test_builds_instagram_oauth_url_not_facebook(self, monkeypatch):
        from app.core.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "INSTAGRAM_APP_ID", "123456")

        adapter = InstagramLoginAdapter()
        request = adapter.build_authorization_url(state="abc", redirect_uri="https://example.com/callback")

        assert request.authorization_url.startswith("https://www.instagram.com/oauth/authorize?")
        assert "client_id=123456" in request.authorization_url
        assert "state=abc" in request.authorization_url
        assert "instagram_business_basic" in request.authorization_url

    def test_missing_app_id_raises_configuration_error(self, monkeypatch):
        from app.core.config import get_settings

        settings = get_settings()
        monkeypatch.setattr(settings, "INSTAGRAM_APP_ID", None)

        adapter = InstagramLoginAdapter()
        with pytest.raises(InstagramLoginConfigurationError):
            adapter.build_authorization_url(state="abc", redirect_uri="https://example.com/callback")
