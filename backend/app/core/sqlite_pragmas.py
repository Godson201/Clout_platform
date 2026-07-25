from sqlalchemy import Engine, event


def enable_sqlite_wal(engine: Engine, database_url: str) -> None:
    """Phase 2 runs FastAPI's async engine and the Celery task's sync engine
    against the same SQLite file in dev/tests (two separate connection pools).
    SQLite's default rollback-journal mode serializes writers aggressively enough
    to raise "database is locked" under that pattern; WAL mode plus a busy
    timeout lets concurrent readers/writers coexist the way Postgres does by
    default in production. No-op for non-SQLite URLs.
    """
    if "sqlite" not in database_url:
        return

    @event.listens_for(engine.sync_engine if hasattr(engine, "sync_engine") else engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ANN001, ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()
