import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.campaign_slot import CampaignSlot
from app.models.enums import ACTIVE_SLOT_STATUSES, CampaignStatus, NotificationType, SlotStatus
from app.models.influencer import Influencer
from app.services.notifications import notify_user

MAX_ACTIVE_SLOTS_PER_INFLUENCER = 5


async def claim_slot(db: AsyncSession, *, slot_id: uuid.UUID, influencer_id: uuid.UUID) -> CampaignSlot:
    """Atomically claims a slot, enforcing both "still open" and "under 5 active
    slots" in the WHERE clause of a single UPDATE. This is what makes it safe
    under concurrent claims (two influencers racing for the same slot, or one
    influencer double-submitting) — the correlated subquery is evaluated as
    part of the same atomic statement, so there's no gap between checking and
    acting for another request to land in. Deliberately not SELECT ... FOR
    UPDATE: SQLite (used in tests) doesn't support row locking, and a portable
    conditional UPDATE gives the same guarantee on both SQLite and Postgres.
    """
    active_count_subq = (
        select(func.count())
        .select_from(CampaignSlot)
        .where(CampaignSlot.influencer_id == influencer_id, CampaignSlot.status.in_(ACTIVE_SLOT_STATUSES))
        .scalar_subquery()
    )

    stmt = (
        update(CampaignSlot)
        .where(
            CampaignSlot.id == slot_id,
            CampaignSlot.status == SlotStatus.OPEN,
            active_count_subq < MAX_ACTIVE_SLOTS_PER_INFLUENCER,
        )
        .values(status=SlotStatus.CLAIMED, influencer_id=influencer_id, claimed_at=datetime.now(timezone.utc))
    )
    result = await db.execute(stmt)

    if result.rowcount == 1:
        # First claim on a campaign moves it from "listed on the marketplace"
        # to "actively being fulfilled" — harmless to run on every claim (not
        # just the first), since flipping an already-ACTIVE campaign to ACTIVE
        # again is a no-op.
        campaign_id_subq = select(CampaignSlot.campaign_id).where(CampaignSlot.id == slot_id).scalar_subquery()
        await db.execute(
            update(Campaign)
            .where(Campaign.id == campaign_id_subq, Campaign.status == CampaignStatus.LISTED)
            .values(status=CampaignStatus.ACTIVE)
        )

    await db.commit()

    if result.rowcount == 0:
        # Not part of the atomicity guarantee above — just figuring out which
        # error message to show. A second read here can't un-race the claim;
        # it can only explain why the UPDATE above already didn't happen.
        slot = await db.get(CampaignSlot, slot_id)
        if slot is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found")
        if slot.status != SlotStatus.OPEN:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slot is no longer available")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You already have {MAX_ACTIVE_SLOTS_PER_INFLUENCER} active slots — the maximum allowed at once",
        )

    fresh = await db.execute(
        select(CampaignSlot).where(CampaignSlot.id == slot_id).execution_options(populate_existing=True)
    )
    slot = fresh.scalar_one()

    campaign = await db.get(Campaign, slot.campaign_id)
    influencer = await db.get(Influencer, influencer_id)
    if campaign is not None and influencer is not None:
        await notify_user(
            db,
            user_id=campaign.brand_id,
            type_=NotificationType.SLOT_CLAIMED,
            title=f"{influencer.display_name} claimed a slot",
            body=f"{influencer.display_name} (@{influencer.username}) claimed a {slot.platform.value} slot on your campaign.",
            link=f"/brand/campaigns/{campaign.id}",
            data={"campaign_id": str(campaign.id), "slot_id": str(slot.id), "influencer_id": str(influencer.id)},
        )

    return slot
