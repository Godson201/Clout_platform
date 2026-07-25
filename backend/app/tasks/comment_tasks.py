import asyncio
import logging

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.db import AsyncSessionLocal
from app.models.enums import SocialPostStatus
from app.models.social_post import SocialPost
from app.services.social_comments import poll_post_comments

logger = logging.getLogger("clout.tasks")

# Same split as the other tasks/*.py modules: this async function is the real,
# directly-testable logic; the @celery_app.task below is a thin asyncio.run()
# adapter, kept separate so tests can await it without going through Celery's
# eager-mode dispatch (which would call asyncio.run() from inside
# pytest-asyncio's already-running loop and raise).


async def poll_all_active_post_comments() -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SocialPost).where(SocialPost.status == SocialPostStatus.PUBLISHED))
        posts = result.scalars().all()

        total_new = 0
        for post in posts:
            try:
                new_comments = await poll_post_comments(db, post=post)
                total_new += len(new_comments)
            except Exception:
                logger.exception("Failed to poll comments for post %s", post.id)
        return total_new


@celery_app.task(name="poll_all_active_post_comments")
def poll_all_active_post_comments_task() -> int:
    return asyncio.run(poll_all_active_post_comments())
