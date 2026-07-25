import os
import shutil
import subprocess
import tempfile

# Must be set before any `app.*` module is imported, since app.core.db /
# app.core.db_sync / app.services.storage build engines and paths from settings
# at import time. Tests run against SQLite so contributors don't need
# Postgres/Docker installed just to run the suite; Alembic + Postgres remain the
# source of truth for the real schema (see backend/README.md).
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")
_TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="clout-test-media-")
os.environ.setdefault("MEDIA_ROOT", _TEST_MEDIA_ROOT)
# No Redis/worker in the test environment — Celery tasks run synchronously
# in-process (see app/core/celery_app.py).
os.environ.setdefault("CELERY_TASK_ALWAYS_EAGER", "true")
# Fixed but valid Fernet key — fine for tests, never used outside this process.
os.environ.setdefault("SOCIAL_TOKEN_ENCRYPTION_KEY", "zHz0jfvz0jz3aRXKz6nZ0J8qgq7z5r1v2yV3wq9F1lE=")
os.environ.setdefault("SOCIAL_OAUTH_MODE", "mock")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

import app.models  # noqa: F401
from app.core.db import Base, engine
from app.main import app as fastapi_app
from app.seeds.seed import (
    seed_advertisement_templates,
    seed_external_wallet,
    seed_fee_config,
    seed_platform_wallet,
    seed_roles_and_permissions,
    seed_view_rates,
)


@pytest_asyncio.fixture(autouse=True)
async def _fresh_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from app.core.db import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        await seed_roles_and_permissions(db)
        await seed_advertisement_templates(db)
        await seed_view_rates(db)
        await seed_fee_config(db)
        await seed_platform_wallet(db)
        await seed_external_wallet(db)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="session", autouse=True)
def _cleanup_media_root():
    yield
    shutil.rmtree(_TEST_MEDIA_ROOT, ignore_errors=True)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="session")
def tiny_video_bytes() -> bytes:
    """A ~2s synthetic 320x240 mp4 generated once per test session via ffmpeg's
    `lavfi` test-source input — exercises the real probe/transcode pipeline
    instead of mocking it, matching how Phase 1 was verified against real
    behavior rather than stubs.
    """
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "sample.mp4")
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc=duration=2:size=320x240:rate=10",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=1000:duration=2",
                "-c:v",
                "libx264",
                "-c:a",
                "aac",
                "-t",
                "2",
                path,
            ],
            capture_output=True,
            check=True,
            timeout=60,
        )
        with open(path, "rb") as f:
            return f.read()
