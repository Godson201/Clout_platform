import hashlib
import hmac
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.models.enums import PaymentStatus
from app.models.payment import Payment
from app.models.payout import Payout
from app.models.refund import Refund
from app.schemas.payment import MoMoWebhookPayload
from app.services.campaign_funding import confirm_campaign_funding, fail_campaign_funding
from app.services.payouts import confirm_payout, fail_payout
from app.services.refunds import confirm_refund, fail_refund

router = APIRouter(prefix="/webhooks/momo", tags=["payments"])
logger = logging.getLogger("clout")
settings = get_settings()

_STATUS_MAP = {
    "SUCCESSFUL": PaymentStatus.SUCCESSFUL,
    "FAILED": PaymentStatus.FAILED,
    "PENDING": PaymentStatus.PENDING,
}


async def _verify_signature(request: Request) -> None:
    """MTN MoMo callbacks are server-to-server, not user-authenticated — this is
    the only auth on this endpoint, so it matters. Verification is skipped only
    when MOMO_WEBHOOK_SECRET isn't configured (mock/dev mode, where there is no
    real MoMo sending callbacks); it's mandatory the moment a real secret is set.
    """
    if not settings.MOMO_WEBHOOK_SECRET:
        logger.warning("MOMO_WEBHOOK_SECRET not configured — skipping webhook signature verification (dev/mock only)")
        return

    signature = request.headers.get("X-Momo-Signature")
    if not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing webhook signature")

    body = await request.body()
    expected = hmac.new(settings.MOMO_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")


@router.post("/collection", status_code=status.HTTP_204_NO_CONTENT)
async def momo_collection_webhook(
    request: Request, payload: MoMoWebhookPayload, db: AsyncSession = Depends(get_db)
) -> None:
    await _verify_signature(request)

    result = await db.execute(select(Payment).where(Payment.provider_reference == payload.referenceId))
    payment = result.scalar_one_or_none()
    if payment is None:
        # Not an error worth surfacing to MoMo as a failure — an unknown reference
        # just means this callback doesn't correspond to anything we tracked.
        logger.warning("MoMo collection webhook for unknown reference %s", payload.referenceId)
        return

    incoming_status = _STATUS_MAP.get(payload.status.upper(), PaymentStatus.PENDING)
    if incoming_status == PaymentStatus.SUCCESSFUL:
        await confirm_campaign_funding(db, payment=payment)
    elif incoming_status == PaymentStatus.FAILED:
        await fail_campaign_funding(db, payment=payment, reason=payload.reason)


@router.post("/disbursement", status_code=status.HTTP_204_NO_CONTENT)
async def momo_disbursement_webhook(
    request: Request, payload: MoMoWebhookPayload, db: AsyncSession = Depends(get_db)
) -> None:
    """Disbursements cover both influencer payouts and brand refunds — both use
    MoMo's Disbursements product and share this one callback path, disambiguated
    by which table actually has a row for the reference."""
    await _verify_signature(request)

    incoming_status = _STATUS_MAP.get(payload.status.upper(), PaymentStatus.PENDING)

    payout_result = await db.execute(select(Payout).where(Payout.provider_reference == payload.referenceId))
    payout = payout_result.scalar_one_or_none()
    if payout is not None:
        if incoming_status == PaymentStatus.SUCCESSFUL:
            await confirm_payout(db, payout=payout)
        elif incoming_status == PaymentStatus.FAILED:
            await fail_payout(db, payout=payout, reason=payload.reason)
        return

    refund_result = await db.execute(select(Refund).where(Refund.provider_reference == payload.referenceId))
    refund = refund_result.scalar_one_or_none()
    if refund is not None:
        if incoming_status == PaymentStatus.SUCCESSFUL:
            await confirm_refund(db, refund=refund)
        elif incoming_status == PaymentStatus.FAILED:
            await fail_refund(db, refund=refund, reason=payload.reason)
        return

    logger.warning("MoMo disbursement webhook for unknown reference %s", payload.referenceId)
