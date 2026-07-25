# CLOUT — Phase 1 + Phase 2 + Phase 3

Influencer marketing & ads distribution platform. Phase 1 delivers authentication,
RBAC, brand/influencer profiles, admin user & verification management, and the
wallet/ledger schema skeleton that later payment phases build on. Phase 2 adds the
Brand Toolkit: ad templates, advertisement creation, media upload, and FFmpeg-based
multi-platform video transcoding. Phase 3 adds campaign creation, view-based
pricing, the influencer marketplace, weighted-scoring matching, and slot claiming.

## Stack

- **Backend**: FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Alembic, Argon2 password
  hashing, PyJWT access tokens + rotating httpOnly-cookie refresh tokens, Celery +
  Redis for background video processing, FFmpeg for transcoding.
- **Frontend**: Next.js (App Router), TypeScript, Tailwind, shadcn/ui, TanStack Query,
  Zustand.
- **FFmpeg/ffprobe must be on `PATH`** — required by `app/services/video_processing.py`
  and by the test suite's real-transcode test.

## Running it

### 1. Start Postgres + Redis

```
docker compose up -d db redis
```

Phase 2 also needs a Celery worker to actually process uploaded videos:
`docker compose up -d celery-worker` (or, for local dev without Docker, leave
`CELERY_TASK_ALWAYS_EAGER=true` in `backend/.env` — uploads are then transcoded
synchronously in-process, no worker needed; see "Background video processing"
below).

### 2. Backend

```
cd backend
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash; use .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env            # then edit JWT_SECRET_KEY, SEED_ADMIN_EMAIL/PASSWORD
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
python -m app.seeds.seed        # seeds roles/permissions, platform wallet, admin user
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/api/v1/docs

**Note on email addresses**: `email-validator` rejects reserved/special-use TLDs
(`.local`, `.test`, `.example`, `.invalid`) — don't use those for `SEED_ADMIN_EMAIL`
or test accounts.

### 3. Frontend

```
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open http://localhost:3000.

### Running tests

```
cd backend
pytest
```

Tests run against SQLite (`tests/conftest.py` sets `DATABASE_URL` before any app
module is imported) so contributors don't need Postgres/Docker just to run the
suite. Alembic + Postgres remain the source of truth for the real schema — the
autogenerate step above must be run against a live Postgres instance at least
once to produce `alembic/versions/`.

The Phase 2 test suite includes a **real** FFmpeg pipeline test (no mocks): a
tiny synthetic clip is generated via `ffmpeg -f lavfi` once per test session,
uploaded through the API, and asserted to come back `ready` with all four
platform renditions transcoded to 1080x1920 — this requires FFmpeg on `PATH`.

## What's in Phase 1

- Email/password auth, JWT access tokens (15 min), rotating refresh tokens
  (30 days, httpOnly cookie, single-use — replay of a rotated token is rejected).
- RBAC: `roles` / `permissions` / `user_roles` / `role_permissions`, seeded with
  `brand`, `influencer`, `admin`. Admin permissions are scoped via `permissions`
  rows rather than new roles, per the architecture discussion (Finance/Moderator/
  Support are meant to become permission subsets of `admin`, not new tables).
- Brand and influencer profile CRUD (`/brands/me`, `/influencers/me`).
- Admin: list/filter/paginate users, suspend/reactivate, verify/reject brands
  and influencers. Every sensitive mutation writes an `audit_logs` row.
- Wallet schema (`wallets`, `transactions`) created and a wallet auto-provisioned
  per brand/influencer/platform at account-creation time — **no money moves yet**;
  this exists now so Phase 4 (MoMo/escrow) doesn't retrofit the ledger under live
  balances.
- No public admin-registration endpoint by design — admins are created only via
  `python -m app.seeds.seed`, reading `SEED_ADMIN_EMAIL`/`SEED_ADMIN_PASSWORD`.

## What's in Phase 2

- **Advertisement templates**: 13 seeded categories matching the product spec
  (product/service/campaign/e-commerce/SaaS/brand visibility/song/movie trailer/
  concert/government/police/RBC/other). Brand-facing read via `/templates`;
  admin CRUD via `/admin/templates` (create/deactivate — the Phase 2 stand-in
  for "template approval").
- **Advertisement creation**: brands build an ad from a template
  (`/advertisements`), editing title/script/CTA/hashtags/duration, with a
  `draft → ready → archived` lifecycle. `ready` requires at least one
  successfully processed video asset; `archived` is read-only.
- **Media upload** (`POST /advertisements/{id}/assets`): video/image/logo/audio/
  voiceover, validated by extension + Content-Type prefix and a streamed,
  enforced size cap (not a trusted Content-Length header) before anything
  touches disk. Storage sits behind a `StorageBackend` interface
  (`app/services/storage.py`) — `LocalStorageBackend` is the only
  implementation today; swapping in S3/MinIO later is a new class behind the
  same interface, not a rewrite.
- **FFmpeg video processing**: every uploaded video is probed (`ffprobe`) and
  transcoded (`ffmpeg`) to one rendition per platform — TikTok, Instagram,
  Facebook, YouTube, all 9:16 1080x1920 per `app/core/platform_specs.py`, which
  also encodes each platform's own max duration and bitrate. Subprocess calls
  always use argument lists, never `shell=True`.
- **Background video processing**: dispatched through Celery
  (`app/core/celery_app.py`). `CELERY_TASK_ALWAYS_EAGER=true` (the local/test
  default) runs the whole pipeline synchronously in-process via a thread pool —
  no Redis or worker needed for local dev. Set it to `false` (docker-compose's
  `backend`/`celery-worker` services already do) once a real worker is
  consuming the queue. The Celery task uses a **separate sync SQLAlchemy
  session** (`app/core/db_sync.py`) rather than the app's async engine, since a
  real worker is a different OS process with no event loop to share — this
  also avoids ever needing `asyncio.run()` inside a task.
- **Frontend**: `/brand/toolkit` (template picker → creates an ad),
  `/brand/ads` (library), `/brand/ads/[id]` (editor — creative fields, media
  upload, live per-platform rendition status via polling while anything is
  still processing).

## What's in Phase 3

- **Pricing**: `base_price = target_views × rate_per_view`, summed **per
  selected platform** (a campaign targeting `[tiktok, instagram]` at 100,000
  views wants 100k on *each*, not 100k split between them — a modeling
  decision documented on the `Campaign` model). CLOUT's confirmed take rate is
  charged on **both sides**: `brand_fee_pct` on top of the brand's payment
  (applied here), `influencer_fee_pct` deducted at payout (Phase 4). Both are
  snapshotted onto the campaign at creation (`rate_snapshot`, `brand_fee_pct`)
  so a later admin rate/fee change never retroactively re-prices an existing
  campaign. Rates (`/admin/view-rates`) and the fee config (`/admin/fee-config`)
  are admin-managed, seeded with placeholder RWF/view defaults.
- **Campaign funding is stubbed** (`POST /campaigns/{id}/fund`): transitions
  status and generates slots with **no real money movement** — Phase 4's MoMo
  integration doesn't exist yet. This is what let marketplace/matching/slots
  get built and tested now, per the roadmap's own phase ordering. See
  `services/campaign_lifecycle.py` for exactly what Phase 4 needs to replace.
- **Slots**: one per (platform, unit) — `slot_count` influencers per selected
  platform, each targeting an even split of that platform's view target
  (`services/campaign_slots.py`). Only `open`/`claimed`/`cancelled` are
  reachable this phase; `published`/`tracking`/`completed`/`failed`/`recovered`
  exist in the `SlotStatus` enum already so Phase 5+ doesn't need another
  migration.
- **Matching** (`services/matching.py`): explainable weighted scoring — sector
  match, location match, follower-tier fit, and historical completion rate
  (neutral default for influencers with no track record yet). Deliberately
  ships without platform-compatibility or engagement-rate factors, since those
  need Phase 5's connected social accounts and real metrics — the score
  breakdown is structured so adding them later doesn't change its shape.
  Follower tier itself is self-reported (`Influencer.follower_tier`) until
  Phase 5 can verify real follower counts.
- **Slot claiming** (`services/slot_claim.py`) is the concurrency-critical
  operation: a single atomic `UPDATE ... WHERE status='open' AND (correlated
  subquery counting active slots) < 5` both prevents double-claims and
  enforces the 5-active-slots-per-influencer rule, without `SELECT ... FOR
  UPDATE` (which SQLite, used in tests, doesn't support) — verified under
  actual concurrent requests (`asyncio.gather`) in
  `tests/test_marketplace_and_slots.py`, not just reasoned about.
- **Frontend**: `/brand/campaigns` (list), `/brand/campaigns/new` (creation
  wizard — pick a ready ad, platforms, tier, slot count), `/brand/campaigns/[id]`
  (pricing breakdown, fund/cancel actions, slot list); `/influencer/marketplace`
  (browse open slots with live match-score breakdown, filter by
  platform/tier, claim), `/influencer/slots` (claimed slots, active count out
  of 5).

## Security notes for this phase

- Passwords hashed with Argon2 (`argon2-cffi`), never logged.
- Access tokens are short-lived (15 min) and held only in frontend memory
  (Zustand), never localStorage — an XSS payload can't read them off disk.
- Refresh tokens are opaque random strings; only their SHA-256 hash is stored,
  so a DB leak doesn't hand out usable tokens. They live in an httpOnly, SameSite=lax
  cookie scoped to `/api/v1/auth`, invisible to JS entirely.
- Refresh token rotation: each `/auth/refresh` call revokes the token it
  consumed and issues a new one — a stolen-then-reused old token is rejected.
- CORS is allow-listed via `CORS_ORIGINS`, not wildcarded.
- All secrets (`JWT_SECRET_KEY`, DB credentials, seed admin password) come from
  `.env`, never hardcoded; `.env` is gitignored, `.env.example` documents the
  shape.
- Uploaded file storage keys are always server-generated UUIDs
  (`generate_storage_key`), never derived from the client's filename — rules
  out path traversal via a crafted upload filename.
- Every advertisement/asset endpoint checks brand ownership and returns 404
  (not 403) for another brand's resources, so existence isn't leaked.
- **Known gap, called out rather than silently skipped**: uploads are
  validated by extension and declared Content-Type only, not by inspecting
  file contents/magic bytes, and there's no malware scanning. Fine for an
  internal MVP; add `python-magic`/ClamAV before accepting untrusted uploads
  in production.

## Not in scope yet (later phases)

MTN MoMo, real escrow settlement and refunds, influencer payouts, social
platform adapters and auto-posting, performance tracking against real view
counts, slot recovery/recycling on underperformance, comment/sentiment AI,
report generation, actual S3/MinIO storage (interface ready, no bucket wired
up), admin frontend UI for template/pricing management (API-only for now) —
per the phased roadmap agreed before implementation started.
