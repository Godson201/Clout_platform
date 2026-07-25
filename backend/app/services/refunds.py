import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.enums import PaymentStatus, TransactionType, WalletOwnerType
from app.models.refund import Refund
from app.services.ledger import get_wallet, record_transaction
from app.services.payments import get_active_provider, get_payment_client


async def refund_campaign_escrow(
    db: AsyncSession, *, campaign: Campaign, phone_number: str, amount: Decimal | None = None
) -> Refund | None:
    """Refunds money from a campaign's escrow wallet back to the brand's MoMo
    number. Two callers: services/campaign_lifecycle.cancel_campaign (no
    `amount` — refunds whatever remains in escrow, when a funded-but-unclaimed
    campaign is cancelled) and services/slot_recovery.py (an explicit `amount`
    — just one slot's unrecoverable shortfall, once its recycle-chain has hit
    MAX_RECOVERY_GENERATIONS). Returns None if there's nothing to refund.
    """
    try:
        escrow_wallet = await get_wallet(
            db, owner_type=WalletOwnerType.ESCROW, owner_id=campaign.id, currency=campaign.currency
        )
    except RuntimeError:
        return None

    refund_amount = Decimal(str(amount)) if amount is not None else Decimal(str(escrow_wallet.balance))
    if refund_amount <= 0:
        return None

    external_wallet = await get_wallet(db, owner_type=WalletOwnerType.EXTERNAL, owner_id=None, currency=campaign.currency)

    hold_ref = str(uuid.uuid4())
    await record_transaction(
        db,
        debit_wallet_id=escrow_wallet.id,
        credit_wallet_id=external_wallet.id,
        amount=refund_amount,
        currency=campaign.currency,
        type=TransactionType.REFUND,
        reference=f"refund:{hold_ref}",
        description=f"Refund hold for cancelled campaign {campaign.id}",
    )

    refund = Refund(
        campaign_id=campaign.id,
        provider=get_active_provider(),
        provider_reference=hold_ref,
        phone_number=phone_number,
        amount=refund_amount,
        currency=campaign.currency,
        status=PaymentStatus.PENDING,
    )
    db.add(refund)
    await db.flush()

    client = get_payment_client()
    try:
        result = await client.initiate_disbursement(
            phone_number=phone_number,
            amount=refund_amount,
            currency=campaign.currency,
            external_id=str(refund.id),
            payee_message=f"CLOUT refund for campaign {campaign.id}",
        )
    except Exception as exc:  # provider unreachable/rejected the request outright
        await _reverse_refund(db, refund=refund, reason=f"Provider error: {exc}")
        return refund

    refund.provider_reference = result.provider_reference
    return refund


async def _reverse_refund(db: AsyncSession, *, refund: Refund, reason: str) -> None:
    escrow_wallet = await get_wallet(
        db, owner_type=WalletOwnerType.ESCROW, owner_id=refund.campaign_id, currency=refund.currency
    )
    external_wallet = await get_wallet(db, owner_type=WalletOwnerType.EXTERNAL, owner_id=None, currency=refund.currency)

    await record_transaction(
        db,
        debit_wallet_id=external_wallet.id,
        credit_wallet_id=escrow_wallet.id,
        amount=Decimal(str(refund.amount)),
        currency=refund.currency,
        type=TransactionType.ADJUSTMENT,
        reference=f"refund-reversal:{refund.provider_reference}",
        description=f"Reversal of failed refund {refund.id}: {reason}",
        enforce_sufficient_balance=False,
    )
    refund.status = PaymentStatus.FAILED
    refund.failure_reason = reason


async def confirm_refund(db: AsyncSession, *, refund: Refund) -> Refund:
    stmt = (
        update(Refund)
        .where(Refund.id == refund.id, Refund.status == PaymentStatus.PENDING)
        .values(status=PaymentStatus.SUCCESSFUL, completed_at=datetime.now(timezone.utc))
    )
    await db.execute(stmt)
    await db.commit()
    refreshed = await db.execute(select(Refund).where(Refund.id == refund.id))
    return refreshed.scalar_one()


async def fail_refund(db: AsyncSession, *, refund: Refund, reason: str | None) -> Refund:
    stmt = (
        update(Refund)
        .where(Refund.id == refund.id, Refund.status == PaymentStatus.PENDING)
        .values(status=PaymentStatus.FAILED, failure_reason=reason)
    )
    result = await db.execute(stmt)
    if result.rowcount > 0:
        await _reverse_refund(db, refund=refund, reason=reason or "Disbursement failed at provider")
    await db.commit()
    refreshed = await db.execute(select(Refund).where(Refund.id == refund.id))
    return refreshed.scalar_one()


async def sync_refund_status(db: AsyncSession, *, refund: Refund) -> Refund:
    if refund.status != PaymentStatus.PENDING:
        return refund

    client = get_payment_client()
    result = await client.get_disbursement_status(refund.provider_reference)

    if result.status == PaymentStatus.SUCCESSFUL:
        return await confirm_refund(db, refund=refund)
    if result.status == PaymentStatus.FAILED:
        return await fail_refund(db, refund=refund, reason=result.failure_reason)
    return refund
