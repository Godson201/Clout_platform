import asyncio
import logging

from app.core.celery_app import celery_app
from app.core.db import AsyncSessionLocal
from app.services.auto_settlement import auto_settle_expired_slots

logger = logging.getLogger("clout.tasks")

# Same split as payment_reconciliation_tasks.py / social_metrics_tasks.py: this
# async function is the real, directly-testable logic; the @celery_app.task
# below is a thin asyncio.run() adapter, kept separate so tests can await it
# without going through Celery's eager-mode dispatch (which would call
# asyncio.run() from inside pytest-asyncio's already-running loop and raise).


async def run_auto_settlement() -> dict[str, int]:
    async with AsyncSessionLocal() as db:
        try:
            return await auto_settle_expired_slots(db)
        except Exception:
            logger.exception("Auto-settlement run failed")
            raise


@celery_app.task(name="run_auto_settlement")
def run_auto_settlement_task() -> dict[str, int]:
    return asyncio.run(run_auto_settlement())
