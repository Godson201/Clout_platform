from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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
        psycopg2_url = async_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        # Settings._normalize_database_url renamed sslmode -> ssl for asyncpg's
        # benefit (see core/config.py) — psycopg2 only understands the
        # original libpq name, so it has to be renamed back here or every
        # sync (Celery-task) connection fails outright with "invalid DSN
        # query parameter: ssl".
        parts = urlsplit(psycopg2_url)
        query = dict(parse_qsl(parts.query))
        ssl_value = query.pop("ssl", None)
        if ssl_value:
            query["sslmode"] = ssl_value
        new_query = urlencode(query)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, new_query, parts.fragment))
    if async_url.startswith("sqlite+aiosqlite://"):
        return async_url.replace("sqlite+aiosqlite://", "sqlite://", 1)
    return async_url


_sync_database_url = _sync_url(settings.DATABASE_URL)
sync_engine = create_engine(_sync_database_url, pool_pre_ping=True, future=True)
enable_sqlite_wal(sync_engine, _sync_database_url)
SyncSessionLocal = sessionmaker(bind=sync_engine, autoflush=False, expire_on_commit=False)
