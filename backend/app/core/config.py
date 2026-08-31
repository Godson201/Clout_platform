from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "postgresql+asyncpg://clout:clout@localhost:5432/clout"

    @field_validator("DATABASE_URL")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        # Managed Postgres providers (Railway, Heroku, Render, Neon) inject a
        # plain postgres:// or postgresql:// URL — the async engine needs the
        # +asyncpg driver prefix explicitly, so upgrade it here rather than
        # asking every deploy target to know about our driver choice.
        if value.startswith("postgres://"):
            value = "postgresql+asyncpg://" + value[len("postgres://") :]
        elif value.startswith("postgresql://"):
            value = "postgresql+asyncpg://" + value[len("postgresql://") :]
        elif not value.startswith("postgresql+asyncpg://"):
            return value

        # These providers also commonly append libpq-style query params
        # (sslmode, channel_binding) — asyncpg's connect() doesn't accept a
        # "sslmode" keyword at all (TypeError: unexpected keyword argument),
        # but its "ssl" keyword accepts the exact same enum strings
        # ("require", "verify-full", ...), so renaming the key is enough;
        # the value itself needs no translation. channel_binding has no
        # asyncpg equivalent and is safe to drop for our connection needs.
        parts = urlsplit(value)
        query = dict(parse_qsl(parts.query))
        sslmode = query.pop("sslmode", None)
        query.pop("channel_binding", None)
        if sslmode:
            query["ssl"] = sslmode
        new_query = urlencode(query)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    DEFAULT_CURRENCY: str = "RWF"

    # Bootstrap admin, consumed only by `python -m app.seeds.seed`. Left unset in
    # most environments — there is no public admin-registration endpoint.
    SEED_ADMIN_EMAIL: str | None = None
    SEED_ADMIN_PASSWORD: str | None = None

    # Local-filesystem stand-in for S3-compatible object storage (see
    # app/services/storage.py). Swapping to a real bucket later means adding an
    # S3StorageBackend behind the same interface, not touching call sites.
    MEDIA_ROOT: str = "./media"
    MAX_VIDEO_UPLOAD_MB: int = 200
    MAX_IMAGE_UPLOAD_MB: int = 10
    MAX_AUDIO_UPLOAD_MB: int = 20
    MAX_DOCUMENT_UPLOAD_MB: int = 20

    # Local/test uses "bypass" so contributors do not need a daemon. Production
    # must use ClamAV's clamd INSTREAM protocol and fails startup otherwise.
    MALWARE_SCANNER_MODE: str = "bypass"
    CLAMAV_HOST: str = "localhost"
    CLAMAV_PORT: int = 3310

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"
    # True when there's no Redis/worker to talk to (local dev, tests): tasks run
    # synchronously in-process instead of being queued. Flip to False once the
    # docker-compose redis + celery-worker services are actually running.
    CELERY_TASK_ALWAYS_EAGER: bool = True

    # "mock" (default) simulates MTN MoMo synchronously with no external calls —
    # used for local dev and the whole test suite, since no sandbox MoMo
    # credentials exist in this environment. Flip to "momo" once real Collections/
    # Disbursements API credentials are available; no call site changes needed,
    # see app/services/payments/__init__.py.
    PAYMENT_PROVIDER_MODE: str = "mock"

    MOMO_BASE_URL: str = "https://sandbox.momodeveloper.mtn.com"
    MOMO_COLLECTIONS_SUBSCRIPTION_KEY: str | None = None
    MOMO_COLLECTIONS_API_USER: str | None = None
    MOMO_COLLECTIONS_API_KEY: str | None = None
    MOMO_DISBURSEMENTS_SUBSCRIPTION_KEY: str | None = None
    MOMO_DISBURSEMENTS_API_USER: str | None = None
    MOMO_DISBURSEMENTS_API_KEY: str | None = None
    MOMO_TARGET_ENVIRONMENT: str = "sandbox"
    # HMAC secret used to verify MoMo webhook signatures (see api/v1/payments.py).
    MOMO_WEBHOOK_SECRET: str | None = None

    # Fernet key (44-char urlsafe base64) encrypting SocialAccount OAuth tokens at
    # rest. Required in every environment, not just production — generate with:
    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    SOCIAL_TOKEN_ENCRYPTION_KEY: str

    # "mock" (default) simulates every platform's OAuth + publish + metrics APIs
    # deterministically, no external calls — used for local dev and the whole
    # test suite, mirroring PAYMENT_PROVIDER_MODE. Flip to "live" once a
    # platform's real app credentials below are filled in AND that platform has
    # actually been granted the relevant API access (see app/services/social/*
    # for why auto-publish/metrics aren't available on every platform by default).
    SOCIAL_OAUTH_MODE: str = "mock"

    # Used to build the OAuth redirect_uri (".../social/callback/{platform}")
    # every provider sends the user's browser back to.
    FRONTEND_BASE_URL: str = "http://localhost:3000"

    # This backend's own publicly reachable origin — used to turn a rendition's
    # /media/... storage path into an absolute URL platform APIs can fetch
    # (TikTok's PULL_FROM_URL, YouTube's upload). Only meaningful once the
    # backend is actually internet-reachable and MEDIA_ROOT is real object
    # storage rather than a local disk (see app/services/storage.py).
    PUBLIC_BASE_URL: str = "http://localhost:8000"

    TIKTOK_CLIENT_KEY: str | None = None
    TIKTOK_CLIENT_SECRET: str | None = None

    META_APP_ID: str | None = None
    META_APP_SECRET: str | None = None

    # Separate from META_APP_ID/SECRET on purpose: "Instagram API with
    # Instagram Login" is a distinct Meta product from classic Facebook
    # Login-based Instagram access, with its own app credentials and OAuth
    # host (see app/services/social/instagram_login.py) — not just a scope
    # difference on the same app.
    INSTAGRAM_APP_ID: str | None = None
    INSTAGRAM_APP_SECRET: str | None = None

    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None

    # "template" (default) fills a fixed narrative template with numbers pulled
    # straight from CampaignAnalytics — always available, never fabricates
    # anything since there's no free-text generation involved. "anthropic" asks
    # Claude to write a more natural narrative from the same verified numbers,
    # then runs every generated report through validate_narrative_numbers
    # (services/report_generation/validation.py) before it's ever shown to a
    # brand — falling back to the template if a number can't be verified.
    REPORT_GENERATOR_MODE: str = "template"
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-sonnet-4-5"

    # "mock" (default) never makes a network call — it logs and keeps sent
    # messages in memory (see app/services/email/console.py), used for local dev
    # without SMTP configured and for the whole test suite. "smtp" sends real
    # mail via SMTP_*, mirroring PAYMENT_PROVIDER_MODE/SOCIAL_OAUTH_MODE.
    EMAIL_MODE: str = "mock"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str | None = None
    SMTP_FROM_NAME: str = "CLOUT"
    EMAIL_VERIFICATION_EXPIRE_MINUTES: int = 60 * 24
    PASSWORD_RESET_EXPIRE_MINUTES: int = 60

    @model_validator(mode="after")
    def _validate_production_security(self) -> "Settings":
        """Reject configurations that would silently expose mock or insecure
        integrations after a production deployment.
        """
        if self.ENVIRONMENT != "production":
            return self

        insecure_values = {"", "change-me-to-a-long-random-value", "test-secret-key-not-for-production"}
        if self.JWT_SECRET_KEY in insecure_values or len(self.JWT_SECRET_KEY) < 32:
            raise ValueError("JWT_SECRET_KEY must be a unique value of at least 32 characters in production")
        if self.PAYMENT_PROVIDER_MODE == "mock":
            raise ValueError("PAYMENT_PROVIDER_MODE=mock is not permitted in production")
        if self.PAYMENT_PROVIDER_MODE == "momo" and not self.MOMO_WEBHOOK_SECRET:
            raise ValueError("MOMO_WEBHOOK_SECRET is required when MTN MoMo is enabled in production")
        if self.SOCIAL_OAUTH_MODE == "mock":
            raise ValueError("SOCIAL_OAUTH_MODE=mock is not permitted in production")
        if self.EMAIL_MODE == "mock":
            raise ValueError("EMAIL_MODE=mock is not permitted in production")
        if self.MALWARE_SCANNER_MODE != "clamav":
            raise ValueError("MALWARE_SCANNER_MODE=clamav is required in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
