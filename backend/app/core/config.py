from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "postgresql+asyncpg://clout:clout@localhost:5432/clout"

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
