import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.campaign_slot import CampaignSlot


async def brand_and_influencer_are_connected(db: AsyncSession, *, brand_id: uuid.UUID, influencer_id: uuid.UUID) -> bool:
    """True once an influencer has claimed at least one slot on one of a brand's
    campaigns — any slot status counts, since even a since-cancelled slot means
    they had a legitimate interaction. This is the one gate messaging, contracts,
    and (later) public-profile visibility all share: it keeps CLOUT from becoming
    an open directory anyone can cold-message.
    """
    stmt = (
        select(CampaignSlot.id)
        .join(Campaign, CampaignSlot.campaign_id == Campaign.id)
        .where(Campaign.brand_id == brand_id, CampaignSlot.influencer_id == influencer_id)
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None
