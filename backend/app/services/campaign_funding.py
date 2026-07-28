import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.enums import CampaignStatus, NotificationType, PaymentStatus, TransactionType, WalletOwnerType
from app.models.payment import Payment
from app.services.audit import write_audit_log
from app.services.campaign_slots import create_slots_for_campaign
from app.services.ledger import get_or_create_wallet, get_wallet, record_transaction
from app.services.notifications import notify_user
from app.services.payments import get_active_provider, get_payment_client


async def initiate_campaign_funding(db: AsyncSession, *, campaign: Campaign, phone_number: str) -> Payment:
    """Starts a MoMo "request to pay" for the campaign's total_brand_payment.
    Real MoMo Collections are asynchronous — this returns a PENDING Payment; the
    brand actually gets funded once confirm_campaign_funding runs, triggered by
    either the webhook (api/v1/payments.py) or the reconciliation task
    (app/tasks/payment_reconciliation_tasks.py) polling provider status.
    """
    if campaign.status not in (CampaignStatus.DRAFT, CampaignStatus.PENDING_FUNDING):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot fund a campaign in status '{campaign.status.value}'",
        )

    # A brand re-submitting /fund while a request is already in flight gets the
    # same Payment back rather than opening a second concurrent collection.
    existing = await db.execute(
        select(Payment).where(Payment.campaign_id == campaign.id, Payment.status == PaymentStatus.PENDING)
    )
    pending_payment = existing.scalar_one_or_none()
    if pending_payment is not None:
        return pending_payment

    client = get_payment_client()
    result = await client.initiate_collection(
        phone_number=phone_number,
        amount=Decimal(str(campaign.total_brand_payment)),
        currency=campaign.currency,
        external_id=str(campaign.id),
        payer_message=f"CLOUT campaign {campaign.id}",
    )

    payment = Payment(
        campaign_id=campaign.id,
        provider=get_active_provider(),
        provider_reference=result.provider_reference,
        phone_number=phone_number,
        amount=campaign.total_brand_payment,
        currency=campaign.currency,
        status=result.status,
    )
    db.add(payment)
    campaign.status = CampaignStatus.PENDING_FUNDING

    await db.commit()
    await db.refresh(payment)
    return payment


async def confirm_campaign_funding(db: AsyncSession, *, payment: Payment) -> Payment:
    """Idempotent: the conditional UPDATE transitions Payment.status PENDING ->
    SUCCESSFUL exactly once, so a duplicated webhook delivery (Scenario I from
    the original payment-integrity analysis — MoMo retries callbacks) or a
    reconciliation poll racing a webhook can't double-credit escrow. Any caller
    that loses the race just gets back the already-settled row.
    """
    stmt = (
        update(Payment)
        .where(Payment.id == payment.id, Payment.status == PaymentStatus.PENDING)
        .values(status=PaymentStatus.SUCCESSFUL, confirmed_at=datetime.now(timezone.utc))
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        await db.commit()
        refreshed = await db.execute(select(Payment).where(Payment.id == payment.id))
        return refreshed.scalar_one()

    campaign_result = await db.execute(select(Campaign).where(Campaign.id == payment.campaign_id))
    campaign = campaign_result.scalar_one()

    escrow_wallet = await get_or_create_wallet(
        db, owner_type=WalletOwnerType.ESCROW, owner_id=campaign.id, currency=campaign.currency
    )
    external_wallet = await get_wallet(db, owner_type=WalletOwnerType.EXTERNAL, owner_id=None, currency=campaign.currency)
    platform_wallet = await get_wallet(db, owner_type=WalletOwnerType.PLATFORM, owner_id=None, currency=campaign.currency)

    base_price = Decimal(str(campaign.base_price))
    fee_amount = Decimal(str(campaign.total_brand_payment)) - base_price

    # The performance-contingent portion goes to escrow...
    await record_transaction(
        db,
        debit_wallet_id=external_wallet.id,
        credit_wallet_id=escrow_wallet.id,
        amount=base_price,
        currency=campaign.currency,
        type=TransactionType.FUNDING,
        reference=f"funding:{payment.provider_reference}",
        description=f"Campaign {campaign.id} funded via {payment.provider.value}",
        enforce_sufficient_balance=False,  # external is a clearing account, allowed to go negative
    )
    # ...the brand-side platform fee is earned immediately, not contingent on performance.
    if fee_amount > 0:
        await record_transaction(
            db,
            debit_wallet_id=external_wallet.id,
            credit_wallet_id=platform_wallet.id,
            amount=fee_amount,
            currency=campaign.currency,
            type=TransactionType.FEE,
            reference=f"funding-fee:{payment.provider_reference}",
            description=f"Brand platform fee for campaign {campaign.id}",
            enforce_sufficient_balance=False,
        )

    campaign.status = CampaignStatus.LISTED
    await create_slots_for_campaign(db, campaign)

    await write_audit_log(
        db,
        actor_user_id=None,
        action="campaign.funding_confirmed",
        entity_type="campaign",
        entity_id=campaign.id,
        after={"payment_id": str(payment.id), "amount": str(payment.amount)},
    )

    await notify_user(
        db,
        user_id=campaign.brand_id,
        type_=NotificationType.PAYMENT_CONFIRMED,
        title=f"Payment of {campaign.currency} {payment.amount:,.0f} successful",
        body="Your campaign is now funded and listed for influencers to claim.",
        link=f"/brand/campaigns/{campaign.id}",
        data={"campaign_id": str(campaign.id), "payment_id": str(payment.id), "amount": str(payment.amount)},
    )

    await db.commit()
    refreshed = await db.execute(select(Payment).where(Payment.id == payment.id))
    return refreshed.scalar_one()


async def fail_campaign_funding(db: AsyncSession, *, payment: Payment, reason: str | None) -> Payment:
    stmt = (
        update(Payment)
        .where(Payment.id == payment.id, Payment.status == PaymentStatus.PENDING)
        .values(status=PaymentStatus.FAILED, failure_reason=reason)
    )
    result = await db.execute(stmt)
    if result.rowcount == 0:
        await db.commit()
        refreshed = await db.execute(select(Payment).where(Payment.id == payment.id))
        return refreshed.scalar_one()

    campaign_result = await db.execute(select(Campaign).where(Campaign.id == payment.campaign_id))
    campaign = campaign_result.scalar_one()
    campaign.status = CampaignStatus.PENDING_FUNDING  # brand can retry with /fund again

    await db.commit()
    refreshed = await db.execute(select(Payment).where(Payment.id == payment.id))
    return refreshed.scalar_one()


async def sync_payment_status(db: AsyncSession, *, payment: Payment) -> Payment:
    """Polls the provider directly — used by the reconciliation task to cover
    Scenario H (payment succeeds at the provider but CLOUT never received the
    webhook)."""
    if payment.status != PaymentStatus.PENDING:
        return payment

    client = get_payment_client()
    result = await client.get_collection_status(payment.provider_reference)

    if result.status == PaymentStatus.SUCCESSFUL:
        return await confirm_campaign_funding(db, payment=payment)
    if result.status == PaymentStatus.FAILED:
        return await fail_campaign_funding(db, payment=payment, reason=result.failure_reason)
    return payment
