from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.enums import CampaignStatus, SlotStatus
from app.services.refunds import refund_campaign_escrow


async def cancel_campaign(db: AsyncSession, campaign: Campaign, *, refund_phone_number: str | None = None) -> Campaign:
    if campaign.status in (CampaignStatus.COMPLETED, CampaignStatus.CANCELLED):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Campaign has already finished")

    # A slot that's merely CLAIMED (nothing posted yet) can still be cancelled
    # for free — its budget was never actually deducted from escrow (only
    # settlement does that), so folding it into the campaign-wide refund below
    # is enough, no per-slot ledger action needed. A slot that's PUBLISHED or
    # TRACKING is a different story: the influencer has already done real work
    # (or has views actively accruing), and yanking it away unpaid isn't fair
    # or something a v1 cancellation flow should decide unilaterally — that
    # needs dispute-style resolution, not implemented here.
    unsettleable_in_flight_slots = [s.id for s in campaign.slots if s.status in (SlotStatus.PUBLISHED, SlotStatus.TRACKING)]
    if unsettleable_in_flight_slots:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a campaign with published/tracking slots — settle them first",
        )

    # A campaign only ever reaches LISTED/ACTIVE after real escrow funding
    # (see services/campaign_funding.py), so only those statuses can have money
    # to refund. DRAFT/PENDING_FUNDING campaigns were never actually charged.
    if campaign.status in (CampaignStatus.LISTED, CampaignStatus.ACTIVE):
        if not refund_phone_number:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="phone_number is required to refund a funded campaign's escrow balance",
            )
        await refund_campaign_escrow(db, campaign=campaign, phone_number=refund_phone_number)

    for slot in campaign.slots:
        slot.status = SlotStatus.CANCELLED
    campaign.status = CampaignStatus.CANCELLED

    await db.commit()
    await db.refresh(campaign)
    return campaign
