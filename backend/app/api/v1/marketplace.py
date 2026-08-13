from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_influencer
from app.models.advertisement import Advertisement
from app.models.advertisement_asset import AdvertisementAsset
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.campaign_slot import CampaignSlot
from app.models.enums import AssetModerationStatus, AssetStatus, CampaignStatus, FollowerTier, SlotStatus, SocialPlatform
from app.models.influencer import Influencer
from app.models.user import User
from app.schemas.advertisement import AssetModerationQueueItem
from app.schemas.campaign_slot import MarketplaceSlotRead, MatchScoreBreakdownRead
from app.services.matching import get_active_platforms, get_engagement_rate, get_reliability_score, score_slot_for_influencer
from app.services.recommendations import get_historical_performance_boost
from app.services.storage import get_storage_backend

router = APIRouter(prefix="/marketplace", tags=["marketplace"], dependencies=[Depends(require_influencer)])


async def _get_own_influencer(db: AsyncSession, user: User) -> Influencer:
    influencer = await db.get(Influencer, user.id)
    if influencer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Influencer profile not found")
    return influencer


@router.get("/slots", response_model=list[MarketplaceSlotRead])
async def browse_marketplace_slots(
    user: User = Depends(require_influencer),
    db: AsyncSession = Depends(get_db),
    platform: SocialPlatform | None = None,
    tier: FollowerTier | None = None,
    sector: str | None = None,
    location: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[MarketplaceSlotRead]:
    influencer = await _get_own_influencer(db, user)

    stmt = (
        select(CampaignSlot, Campaign, Advertisement, Brand)
        .join(Campaign, CampaignSlot.campaign_id == Campaign.id)
        .join(Advertisement, Campaign.advertisement_id == Advertisement.id)
        .join(Brand, Campaign.brand_id == Brand.id)
        .where(
            CampaignSlot.status == SlotStatus.OPEN,
            Campaign.status.in_([CampaignStatus.LISTED, CampaignStatus.ACTIVE]),
        )
    )

    if platform is not None:
        stmt = stmt.where(CampaignSlot.platform == platform)
    if tier is not None:
        stmt = stmt.where(CampaignSlot.tier == tier)
    if sector is not None:
        stmt = stmt.where(Campaign.target_sector == sector)
    if location is not None:
        stmt = stmt.where(Campaign.target_location == location)

    rows = (await db.execute(stmt)).all()

    # Computed once per request, not per slot — same influencer for every row.
    active_platforms = await get_active_platforms(db, influencer.id)
    engagement_rate = await get_engagement_rate(db, influencer.id)
    reliability_score = await get_reliability_score(db, influencer.id)

    scored: list[MarketplaceSlotRead] = []
    for slot, campaign, advertisement, brand in rows:
        breakdown = score_slot_for_influencer(
            slot, campaign_sector=campaign.target_sector, campaign_location=campaign.target_location,
            influencer=influencer, active_platforms=active_platforms, engagement_rate=engagement_rate,
            reliability_score=reliability_score,
        )
        # Sector/platform/tier vary per slot (unlike the influencer-level
        # factors above), so this is necessarily a per-row query — acceptable
        # at today's marketplace size, same tradeoff already accepted for the
        # in-memory sort/paginate below.
        historical = await get_historical_performance_boost(
            db, sector=campaign.target_sector, platform=slot.platform, tier=slot.tier
        )
        final_score = round(breakdown.total * historical.boost, 4)

        scored.append(
            MarketplaceSlotRead(
                id=slot.id,
                campaign_id=slot.campaign_id,
                platform=slot.platform,
                tier=slot.tier,
                target_views=slot.target_views,
                budget_allocated=slot.budget_allocated,
                status=slot.status,
                influencer_id=slot.influencer_id,
                claimed_at=slot.claimed_at,
                created_at=slot.created_at,
                delivered_pct=slot.delivered_pct,
                recovered_from_slot_id=slot.recovered_from_slot_id,
                recovery_generation=slot.recovery_generation,
                brand_name=brand.business_name,
                advertisement_title=advertisement.title,
                campaign_target_sector=campaign.target_sector,
                campaign_target_location=campaign.target_location,
                match_score=MatchScoreBreakdownRead(
                    sector_score=breakdown.sector_score,
                    location_score=breakdown.location_score,
                    tier_score=breakdown.tier_score,
                    reliability_score=breakdown.reliability_score,
                    platform_score=breakdown.platform_score,
                    engagement_score=breakdown.engagement_score,
                    total=breakdown.total,
                ),
                historical_boost=historical.boost,
                final_score=final_score,
            )
        )

    # Sorted/paginated in-memory since ranking depends on a per-influencer score
    # computed after the query, not a DB column — fine at today's data volume;
    # revisit (e.g. materialized score column, DB-side ranking) if the open-slot
    # count grows large enough for this to matter.
    scored.sort(key=lambda s: s.final_score, reverse=True)
    return scored[:limit]


@router.get("/media", response_model=list[AssetModerationQueueItem])
async def browse_approved_media(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AssetModerationQueueItem]:
    """Every asset here already passed admin review (see
    services/asset_moderation.py's approve_asset), which is also what fires
    the NEW_BRAND_MEDIA notification pointing at /influencer/marketplace —
    this is that notification's actual destination: a browsable gallery of
    what brands are looking for, playable directly at original quality, not
    just a bell-icon mention.
    """
    stmt = (
        select(AdvertisementAsset, Advertisement, Brand)
        .join(Advertisement, AdvertisementAsset.advertisement_id == Advertisement.id)
        .join(Brand, Advertisement.brand_id == Brand.id)
        .where(
            AdvertisementAsset.status == AssetStatus.READY,
            AdvertisementAsset.moderation_status == AssetModerationStatus.APPROVED,
        )
        .order_by(AdvertisementAsset.moderated_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()

    storage = get_storage_backend()
    items: list[AssetModerationQueueItem] = []
    for asset, advertisement, brand in rows:
        items.append(
            AssetModerationQueueItem(
                id=asset.id,
                asset_type=asset.asset_type,
                original_filename=asset.original_filename,
                mime_type=asset.mime_type,
                file_size_bytes=asset.file_size_bytes,
                duration_seconds=asset.duration_seconds,
                width=asset.width,
                height=asset.height,
                status=asset.status,
                error_message=asset.error_message,
                created_at=asset.created_at,
                url=storage.url_for(asset.storage_key),
                moderation_status=asset.moderation_status,
                moderation_note=None,
                renditions=[],
                advertisement_id=advertisement.id,
                advertisement_title=advertisement.title,
                brand_name=brand.business_name,
            )
        )
    return items
