from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.campaign_slot import CampaignSlot
from app.models.enums import SocialPlatform


async def create_slots_for_campaign(db: AsyncSession, campaign: Campaign) -> list[CampaignSlot]:
    """One slot per (platform, unit) — `slot_count` influencers per selected
    platform, each targeting an even split of that platform's view target.
    Any remainder from integer division (target_views not evenly divisible by
    slot_count) is simply not allocated to a slot — a known Phase 3
    simplification, not a silent rounding bug: the sum of slot targets can be
    slightly less than campaign.target_views, never more.
    """
    rate_snapshot = {SocialPlatform(k): Decimal(v) for k, v in campaign.rate_snapshot.items()}
    per_slot_views = campaign.target_views // campaign.slot_count

    slots: list[CampaignSlot] = []
    for platform_value in campaign.platforms:
        platform = SocialPlatform(platform_value)
        rate = rate_snapshot[platform]
        for _ in range(campaign.slot_count):
            slot = CampaignSlot(
                campaign_id=campaign.id,
                platform=platform,
                tier=campaign.tier,
                target_views=per_slot_views,
                budget_allocated=Decimal(per_slot_views) * rate,
            )
            db.add(slot)
            slots.append(slot)

    return slots
