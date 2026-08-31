"""Audience rules for brand campaign toolkit media."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.campaign_slot import CampaignSlot
from app.models.advertisement_asset import AdvertisementAsset, AssetShareRecipient
from app.models.enums import AssetDistribution, CampaignStatus, SlotStatus
from app.models.influencer import Influencer


def _matches_targeting(*, campaign: Campaign, influencer: Influencer) -> bool:
    """Match an open campaign's explicit sector, location, and tier rules."""
    if campaign.target_sector and campaign.target_sector.strip().lower() != (influencer.sector or "").strip().lower():
        return False
    if campaign.target_location and campaign.target_location.strip().lower() != (influencer.location or "").strip().lower():
        return False
    return influencer.follower_tier == campaign.tier


async def accessible_asset_ids(db: AsyncSession, *, influencer_id: uuid.UUID) -> set[uuid.UUID]:
    """Return approved toolkit assets this influencer is allowed to receive."""
    influencer = await db.get(Influencer, influencer_id)
    if influencer is None:
        return set()
    rows = (
        await db.execute(
            select(Campaign, CampaignSlot)
            .join(CampaignSlot, CampaignSlot.campaign_id == Campaign.id)
            .where(
                Campaign.status.in_([CampaignStatus.LISTED, CampaignStatus.ACTIVE]),
                CampaignSlot.status != SlotStatus.CANCELLED,
            )
        )
    ).all()
    campaign_advertisement_ids: set[uuid.UUID] = set()
    for campaign, slot in rows:
        if slot.influencer_id == influencer_id or (
            slot.status == SlotStatus.OPEN and _matches_targeting(campaign=campaign, influencer=influencer)
        ):
            campaign_advertisement_ids.add(campaign.advertisement_id)

    assets = (await db.execute(select(AdvertisementAsset))).scalars().all()
    specific_asset_ids = set(
        (await db.execute(select(AssetShareRecipient.asset_id).where(AssetShareRecipient.influencer_id == influencer_id)))
        .scalars()
        .all()
    )
    return {
        asset.id
        for asset in assets
        if asset.distribution == AssetDistribution.ALL_INFLUENCERS
        or (asset.distribution == AssetDistribution.SPECIFIC_INFLUENCERS and asset.id in specific_asset_ids)
        or (asset.distribution == AssetDistribution.CAMPAIGN_ELIGIBLE and asset.advertisement_id in campaign_advertisement_ids)
    }
