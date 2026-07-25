from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings
from app.core.sqlite_pragmas import enable_sqlite_wal

settings = get_settings()

# NullPool-friendly defaults; pool sizing is tuned per-deployment via DATABASE_URL query args.
engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True, future=True)
enable_sqlite_wal(engine, settings.DATABASE_URL)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
