import asyncio
import logging

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.db import AsyncSessionLocal
from app.models.enums import SocialPostStatus
from app.models.social_post import SocialPost
from app.services.social_metrics import poll_post_metrics

logger = logging.getLogger("clout.tasks")

# Same reasoning as app/tasks/payment_reconciliation_tasks.py: the real,
# directly-testable logic is this async function; the @celery_app.task below
# is a thin asyncio.run() adapter, kept separate so tests can await it without
# going through Celery's eager-mode dispatch (which would call asyncio.run()
# from inside pytest-asyncio's already-running loop and raise).


async def poll_all_active_post_metrics() -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SocialPost).where(SocialPost.status == SocialPostStatus.PUBLISHED))
        posts = result.scalars().all()

        polled = 0
        for post in posts:
            try:
                snapshot = await poll_post_metrics(db, post=post)
                if snapshot is not None:
                    polled += 1
            except Exception:
                logger.exception("Failed to poll metrics for post %s", post.id)
        return polled


@celery_app.task(name="poll_all_active_post_metrics")
def poll_all_active_post_metrics_task() -> int:
    """Scheduled (see celery_app.conf.beat_schedule) rather than per-post, since
    a single query naturally skips posts whose platform/mode makes metrics
    unfetchable (poll_post_metrics returns None for those) without needing a
    separate schedule per platform.
    """
    return asyncio.run(poll_all_active_post_metrics())
