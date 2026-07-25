import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.campaign_slot import MAX_RECOVERY_GENERATIONS, CampaignSlot
from app.models.enums import PaymentStatus, SlotStatus
from app.models.payment import Payment
from app.services.refunds import refund_campaign_escrow
from app.services.settlement import maybe_complete_campaign, settle_slot


async def _get_funding_phone_number(db: AsyncSession, *, campaign_id: uuid.UUID) -> str | None:
    """Reuses the MoMo number the brand originally paid with — a shortfall
    refund happens without the brand in the loop (settlement can be triggered
    automatically), so there's no fresh phone number to ask for; refunding to
    the same number that funded the campaign is also just the expected
    behavior for a payment refund.
    """
    result = await db.execute(
        select(Payment)
        .where(Payment.campaign_id == campaign_id, Payment.status == PaymentStatus.SUCCESSFUL)
        .order_by(Payment.confirmed_at.desc())
    )
    payment = result.scalars().first()
    return payment.phone_number if payment is not None else None


async def _create_recovery_slot(
    db: AsyncSession, *, original_slot: CampaignSlot, shortfall_views: int, shortfall_amount: Decimal
) -> CampaignSlot:
    recovery_slot = CampaignSlot(
        campaign_id=original_slot.campaign_id,
        platform=original_slot.platform,
        tier=original_slot.tier,
        target_views=shortfall_views,
        budget_allocated=shortfall_amount,
        status=SlotStatus.OPEN,
        recovered_from_slot_id=original_slot.id,
        recovery_generation=original_slot.recovery_generation + 1,
    )
    db.add(recovery_slot)
    await db.flush()
    return recovery_slot


async def settle_and_recover(
    db: AsyncSession, *, slot: CampaignSlot, delivered_pct: Decimal, actor_user_id: uuid.UUID | None
) -> CampaignSlot:
    """The confirmed recycle-first policy: whatever a slot's escrowed budget
    doesn't cover (delivered_pct < 100) becomes, by default, a fresh OPEN slot
    for another influencer to attempt — never silently left parked, and never
    refunded outright — unless this slot's chain has already been recycled
    MAX_RECOVERY_GENERATIONS times, at which point CLOUT stops retrying and
    returns the remainder to the brand instead. This is the only entry point
    admin_settlement.py and auto_settlement.py should call — settle_slot()
    alone only handles the release, not what happens to the leftover.
    """
    settled_slot = await settle_slot(db, slot=slot, delivered_pct=delivered_pct, actor_user_id=actor_user_id)

    campaign_result = await db.execute(select(Campaign).where(Campaign.id == settled_slot.campaign_id))
    campaign = campaign_result.scalar_one()

    if delivered_pct < 100:
        shortfall_fraction = (Decimal(100) - delivered_pct) / Decimal(100)
        shortfall_views = int(Decimal(settled_slot.target_views) * shortfall_fraction)
        shortfall_amount = (Decimal(str(settled_slot.budget_allocated)) * shortfall_fraction).quantize(
            Decimal("0.0001")
        )

        if shortfall_views > 0 and shortfall_amount > 0:
            if settled_slot.recovery_generation < MAX_RECOVERY_GENERATIONS:
                await _create_recovery_slot(
                    db,
                    original_slot=settled_slot,
                    shortfall_views=shortfall_views,
                    shortfall_amount=shortfall_amount,
                )
            else:
                phone_number = await _get_funding_phone_number(db, campaign_id=campaign.id)
                if phone_number is not None:
                    await refund_campaign_escrow(
                        db, campaign=campaign, phone_number=phone_number, amount=shortfall_amount
                    )
                # No funding record to refund to shouldn't happen in practice —
                # a slot can't exist without a funded campaign — but if it ever
                # does, the shortfall stays in escrow rather than being lost;
                # still visible and recoverable via the ledger.

    await maybe_complete_campaign(db, campaign=campaign)

    await db.commit()
    await db.refresh(settled_slot)
    return settled_slot
