# Phase 1 verification

Run these checks before merging changes:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
$env:DATABASE_URL = "sqlite+aiosqlite:///./migration-check.db"
.\.venv\Scripts\python.exe -m alembic upgrade head

cd ..\frontend
npm.cmd run lint
npm.cmd run build
```

The committed Alembic initial migration is the schema baseline. Never generate a
second initial migration from a developer's existing database. Future schema
changes must be additive Alembic revisions that are reviewed alongside their
model changes.
