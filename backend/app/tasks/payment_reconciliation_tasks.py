import asyncio
import logging

from sqlalchemy import select

from app.core.celery_app import celery_app
from app.core.db import AsyncSessionLocal
from app.models.enums import PaymentStatus
from app.models.payment import Payment
from app.models.payout import Payout
from app.models.refund import Refund
from app.services.campaign_funding import sync_payment_status
from app.services.payouts import sync_payout_status
from app.services.refunds import sync_refund_status

logger = logging.getLogger("clout.tasks")

# Unlike video_processing_tasks (sync DB, since ffmpeg subprocess calls are
# blocking anyway), the funding/payout/refund business logic here is already
# written and tested as async (app/services/*). The `reconcile_*` functions
# below are that real, directly-testable implementation; the @celery_app.task
# wrappers are a thin asyncio.run() adapter — kept separate rather than fused
# so tests can await the real logic directly instead of going through Celery's
# eager-mode dispatch, which would otherwise call asyncio.run() from inside an
# already-running event loop (pytest-asyncio's) and raise.


async def reconcile_pending_payments() -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Payment).where(Payment.status == PaymentStatus.PENDING))
        pending = result.scalars().all()
        for payment in pending:
            try:
                await sync_payment_status(db, payment=payment)
            except Exception:
                logger.exception("Failed to reconcile payment %s", payment.id)
        return len(pending)


async def reconcile_pending_payouts() -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Payout).where(Payout.status == PaymentStatus.PENDING))
        pending = result.scalars().all()
        for payout in pending:
            try:
                await sync_payout_status(db, payout=payout)
            except Exception:
                logger.exception("Failed to reconcile payout %s", payout.id)
        return len(pending)


async def reconcile_pending_refunds() -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Refund).where(Refund.status == PaymentStatus.PENDING))
        pending = result.scalars().all()
        for refund in pending:
            try:
                await sync_refund_status(db, refund=refund)
            except Exception:
                logger.exception("Failed to reconcile refund %s", refund.id)
        return len(pending)


@celery_app.task(name="reconcile_pending_payments")
def reconcile_pending_payments_task() -> int:
    """Covers Scenario H from the payment-integrity design: a MoMo collection
    succeeds at the provider but CLOUT never receives the webhook. Runs on a
    schedule (see celery_app.conf.beat_schedule) polling every Payment stuck
    PENDING — webhooks are the fast path, this is the guaranteed-eventually path.
    """
    return asyncio.run(reconcile_pending_payments())


@celery_app.task(name="reconcile_pending_payouts")
def reconcile_pending_payouts_task() -> int:
    return asyncio.run(reconcile_pending_payouts())


@celery_app.task(name="reconcile_pending_refunds")
def reconcile_pending_refunds_task() -> int:
    return asyncio.run(reconcile_pending_refunds())
