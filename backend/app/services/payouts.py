import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import PaymentStatus, TransactionType, WalletOwnerType
from app.models.influencer import Influencer
from app.models.payout import Payout
from app.services.ledger import InsufficientBalanceError, get_wallet, record_transaction
from app.services.payments import get_active_provider, get_payment_client
from app.services.pricing import get_current_fee_config


async def request_payout(db: AsyncSession, *, influencer: Influencer, amount: Decimal, phone_number: str) -> Payout:
    """Holds the withdrawal amount immediately (both the platform's fee cut and
    the net amount headed to MoMo are moved out of the influencer's wallet
    before the provider is ever called) so a second concurrent withdrawal
    request can't spend the same balance — the atomic conditional UPDATE inside
    record_transaction gives the same guarantee slot claiming relies on. Only
    once the hold succeeds do we call the provider; if that call itself fails,
    the hold is reversed and the Payout is recorded as FAILED rather than lost.
    """
    if amount <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Amount must be positive")

    wallet = await get_wallet(db, owner_type=WalletOwnerType.INFLUENCER, owner_id=influencer.id)
    platform_wallet = await get_wallet(db, owner_type=WalletOwnerType.PLATFORM, owner_id=None)
    external_wallet = await get_wallet(db, owner_type=WalletOwnerType.EXTERNAL, owner_id=None)

    fee_config = await get_current_fee_config(db)
    fee_pct = Decimal(str(fee_config.influencer_fee_pct))
    fee_amount = (amount * fee_pct).quantize(Decimal("0.0001"))
    net_amount = amount - fee_amount

    hold_ref = str(uuid.uuid4())
    try:
        await record_transaction(
            db,
            debit_wallet_id=wallet.id,
            credit_wallet_id=platform_wallet.id,
            amount=fee_amount,
            currency=wallet.currency,
            type=TransactionType.FEE,
            reference=f"payout-fee:{hold_ref}",
            description=f"Influencer platform fee (payout request {hold_ref})",
        )
        await record_transaction(
            db,
            debit_wallet_id=wallet.id,
            credit_wallet_id=external_wallet.id,
            amount=net_amount,
            currency=wallet.currency,
            type=TransactionType.PAYOUT,
            reference=f"payout:{hold_ref}",
            description=f"Payout hold for {phone_number} (request {hold_ref})",
            # enforce_sufficient_balance stays True (the default) here — the
            # debit side is still the influencer's own wallet for this leg too
            # (only the credit side differs between the fee and net legs), and
            # that's a real, finite balance that must never go negative.
        )
    except InsufficientBalanceError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient wallet balance")

    payout = Payout(
        influencer_id=influencer.id,
        provider=get_active_provider(),
        provider_reference=hold_ref,
        phone_number=phone_number,
        amount=amount,
        fee_pct=fee_pct,
        fee_amount=fee_amount,
        net_amount=net_amount,
        currency=wallet.currency,
        status=PaymentStatus.PENDING,
    )
    db.add(payout)
    await db.flush()

    client = get_payment_client()
    try:
        result = await client.initiate_disbursement(
            phone_number=phone_number,
            amount=net_amount,
            currency=wallet.currency,
            external_id=str(payout.id),
            payee_message=f"CLOUT payout {payout.id}",
        )
    except Exception as exc:  # provider unreachable/rejected the request outright
        await _reverse_payout_hold(db, payout=payout, reason=f"Provider error: {exc}")
        await db.commit()
        await db.refresh(payout)
        return payout

    payout.provider_reference = result.provider_reference
    await db.commit()
    await db.refresh(payout)
    return payout


async def _reverse_payout_hold(db: AsyncSession, *, payout: Payout, reason: str) -> None:
    wallet = await get_wallet(db, owner_type=WalletOwnerType.INFLUENCER, owner_id=payout.influencer_id)
    platform_wallet = await get_wallet(db, owner_type=WalletOwnerType.PLATFORM, owner_id=None)
    external_wallet = await get_wallet(db, owner_type=WalletOwnerType.EXTERNAL, owner_id=None)

    await record_transaction(
        db,
        debit_wallet_id=platform_wallet.id,
        credit_wallet_id=wallet.id,
        amount=Decimal(str(payout.fee_amount)),
        currency=payout.currency,
        type=TransactionType.ADJUSTMENT,
        reference=f"payout-reversal-fee:{payout.provider_reference}",
        description=f"Reversal of failed payout {payout.id}: {reason}",
    )
    await record_transaction(
        db,
        debit_wallet_id=external_wallet.id,
        credit_wallet_id=wallet.id,
        amount=Decimal(str(payout.net_amount)),
        currency=payout.currency,
        type=TransactionType.ADJUSTMENT,
        reference=f"payout-reversal:{payout.provider_reference}",
        description=f"Reversal of failed payout {payout.id}: {reason}",
        enforce_sufficient_balance=False,
    )
    payout.status = PaymentStatus.FAILED
    payout.failure_reason = reason


async def confirm_payout(db: AsyncSession, *, payout: Payout) -> Payout:
    """Idempotent PENDING -> SUCCESSFUL transition. No further ledger writes —
    the hold recorded at request time already reflects where the money went."""
    stmt = (
        update(Payout)
        .where(Payout.id == payout.id, Payout.status == PaymentStatus.PENDING)
        .values(status=PaymentStatus.SUCCESSFUL, completed_at=datetime.now(timezone.utc))
    )
    result = await db.execute(stmt)
    await db.commit()
    if result.rowcount == 0:
        refreshed = await db.execute(select(Payout).where(Payout.id == payout.id))
        return refreshed.scalar_one()
    refreshed = await db.execute(select(Payout).where(Payout.id == payout.id))
    return refreshed.scalar_one()


async def fail_payout(db: AsyncSession, *, payout: Payout, reason: str | None) -> Payout:
    """Idempotent PENDING -> FAILED transition, reversing the held funds back to
    the influencer's wallet exactly once."""
    stmt = (
        update(Payout)
        .where(Payout.id == payout.id, Payout.status == PaymentStatus.PENDING)
        .values(status=PaymentStatus.FAILED, failure_reason=reason)
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        await db.commit()
        refreshed = await db.execute(select(Payout).where(Payout.id == payout.id))
        return refreshed.scalar_one()

    await _reverse_payout_hold(db, payout=payout, reason=reason or "Disbursement failed at provider")
    await db.commit()
    refreshed = await db.execute(select(Payout).where(Payout.id == payout.id))
    return refreshed.scalar_one()


async def sync_payout_status(db: AsyncSession, *, payout: Payout) -> Payout:
    if payout.status != PaymentStatus.PENDING:
        return payout

    client = get_payment_client()
    result = await client.get_disbursement_status(payout.provider_reference)

    if result.status == PaymentStatus.SUCCESSFUL:
        return await confirm_payout(db, payout=payout)
    if result.status == PaymentStatus.FAILED:
        return await fail_payout(db, payout=payout, reason=result.failure_reason)
    return payout
