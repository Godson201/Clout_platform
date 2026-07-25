import uuid
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.campaign_slot import CampaignSlot
from app.models.enums import (
    SETTLEABLE_SLOT_STATUSES,
    TERMINAL_SLOT_STATUSES,
    CampaignStatus,
    SlotStatus,
    TransactionType,
    WalletOwnerType,
)
from app.models.influencer import Influencer
from app.services.audit import write_audit_log
from app.services.ledger import get_wallet, record_transaction


async def maybe_complete_campaign(db: AsyncSession, *, campaign: Campaign) -> None:
    """A campaign is done once every one of its slots has landed in a terminal
    state — nothing left that could still change its outcome. Checked after
    every settlement (manual or automatic) rather than eagerly on each slot
    change, since it's cheap and only needs to be right by the time the last
    slot resolves.
    """
    if campaign.status in (CampaignStatus.COMPLETED, CampaignStatus.CANCELLED):
        return

    result = await db.execute(select(CampaignSlot).where(CampaignSlot.campaign_id == campaign.id))
    slots = result.scalars().all()
    if slots and all(s.status in TERMINAL_SLOT_STATUSES for s in slots):
        campaign.status = CampaignStatus.COMPLETED


async def settle_slot(
    db: AsyncSession, *, slot: CampaignSlot, delivered_pct: Decimal, actor_user_id: uuid.UUID | None
) -> CampaignSlot:
    """Releases `delivered_pct` of a slot's escrowed budget to its influencer.
    Two callers, both going through services/slot_recovery.py's
    settle_and_recover() rather than this function directly: the admin manual
    bridge (api/v1/admin_settlement.py) for platforms/posts CLOUT can't verify,
    and Phase 6's automatic settlement (services/auto_settlement.py) for
    platforms where verified metrics are actually available. Which one applies
    to a given slot is decided by platform capability, not by this function —
    by the time this runs, `delivered_pct` has already been decided.

    Deliberately does not commit or check campaign completion — the caller
    (settle_and_recover) still needs to decide what happens to any shortfall
    (recycle into a new slot vs. refund) before either of those should happen,
    and both need to land in the same transaction as this settlement.
    """
    if slot.status not in SETTLEABLE_SLOT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Slot must be claimed, published, or tracking to settle, is '{slot.status.value}'",
        )
    if slot.influencer_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slot has no claiming influencer")
    if not (Decimal(0) <= delivered_pct <= Decimal(100)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="delivered_pct must be between 0 and 100")

    campaign_result = await db.execute(select(Campaign).where(Campaign.id == slot.campaign_id))
    campaign = campaign_result.scalar_one()

    escrow_wallet = await get_wallet(
        db, owner_type=WalletOwnerType.ESCROW, owner_id=campaign.id, currency=campaign.currency
    )
    influencer_wallet = await get_wallet(
        db, owner_type=WalletOwnerType.INFLUENCER, owner_id=slot.influencer_id, currency=campaign.currency
    )

    payable_amount = (Decimal(str(slot.budget_allocated)) * delivered_pct / Decimal(100)).quantize(Decimal("0.0001"))

    if payable_amount > 0:
        settled_by = f"admin {actor_user_id}" if actor_user_id is not None else "automatic window-expiry settlement"
        await record_transaction(
            db,
            debit_wallet_id=escrow_wallet.id,
            credit_wallet_id=influencer_wallet.id,
            amount=payable_amount,
            currency=campaign.currency,
            type=TransactionType.ESCROW_RELEASE,
            reference=f"settlement:{slot.id}",
            description=f"Settlement of slot {slot.id} at {delivered_pct}% delivered ({settled_by})",
        )

    slot.delivered_pct = float(delivered_pct)

    if delivered_pct >= 100:
        slot.status = SlotStatus.COMPLETED
    elif delivered_pct > 0:
        slot.status = SlotStatus.PARTIALLY_COMPLETED
    else:
        slot.status = SlotStatus.FAILED

    influencer_result = await db.execute(select(Influencer).where(Influencer.id == slot.influencer_id))
    influencer = influencer_result.scalar_one()
    if slot.status == SlotStatus.COMPLETED:
        influencer.completed_slots_count += 1
    elif slot.status == SlotStatus.FAILED:
        influencer.failed_slots_count += 1
    # PARTIALLY_COMPLETED feeds neither binary counter — services/matching.py's
    # reliability score reads delivered_pct directly off every terminal slot
    # instead, which naturally weighs a 90%-delivered slot very differently
    # from a 10%-delivered one rather than lumping both in with "failed".

    await write_audit_log(
        db,
        actor_user_id=actor_user_id,
        action="admin.slot.settle" if actor_user_id is not None else "system.slot.auto_settle",
        entity_type="campaign_slot",
        entity_id=slot.id,
        after={
            "delivered_pct": str(delivered_pct),
            "payable_amount": str(payable_amount),
            "status": slot.status.value,
        },
    )

    await db.flush()
    return slot
