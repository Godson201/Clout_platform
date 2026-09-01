"""Record the legacy schema baseline when a database predates Alembic.

Early CLOUT deployments created tables directly from SQLAlchemy metadata.  Such
databases have application tables but no ``alembic_version`` row, so trying to
run the initial Alembic migration would attempt to create those tables again.
This one-time, idempotent bootstrap only stamps the initial revision when that
specific legacy state is detected.  Fresh databases are left untouched and run
the entire migration chain normally.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys

from sqlalchemy import inspect, text

from app.core.db import engine


INITIAL_REVISION = "59ef2ed7528a"


async def needs_legacy_baseline_stamp() -> bool:
    async with engine.connect() as connection:
        has_version_table = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).has_table("alembic_version")
        )
        has_legacy_table = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).has_table("advertisement_templates")
        )
        if not has_legacy_table:
            return False
        if not has_version_table:
            return True
        version = await connection.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))
        return version is None


async def main() -> None:
    try:
        if await needs_legacy_baseline_stamp():
            print(f"Existing schema found without Alembic history; stamping {INITIAL_REVISION}.")
            await engine.dispose()
            subprocess.run([sys.executable, "-m", "alembic", "stamp", INITIAL_REVISION], check=True)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
