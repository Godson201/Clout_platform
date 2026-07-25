from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.sqlite_pragmas import enable_sqlite_wal

settings = get_settings()


def _sync_url(async_url: str) -> str:
    """Celery workers are separate OS processes with no asyncio event loop to
    share, so they use a plain sync SQLAlchemy session rather than reusing the
    app's async engine — that also sidesteps ever needing `asyncio.run()` inside
    a task, which would break the moment a task is dispatched from within an
    already-running event loop (i.e. from a FastAPI request handler).
    """
    if async_url.startswith("postgresql+asyncpg://"):
        return async_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    if async_url.startswith("sqlite+aiosqlite://"):
        return async_url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    return async_url


_sync_database_url = _sync_url(settings.DATABASE_URL)
sync_engine = create_engine(_sync_database_url, pool_pre_ping=True, future=True)
enable_sqlite_wal(sync_engine, _sync_database_url)
SyncSessionLocal = sessionmaker(bind=sync_engine, autoflush=False, expire_on_commit=False)
