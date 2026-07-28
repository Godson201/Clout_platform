import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.advertisement import Advertisement
from app.models.advertisement_asset import AdvertisementAsset
from app.models.brand import Brand
from app.models.enums import AssetModerationStatus, AssetStatus, NotificationType
from app.services.notifications import notify_all_influencers

# LOGO is brand housekeeping, not campaign creative — excluded so influencers
# aren't notified about a brand simply uploading its logo.
_NOTIFIABLE_ASSET_TYPES = {"video", "image", "audio", "voiceover"}


async def list_assets_pending_review(db: AsyncSession) -> list[AdvertisementAsset]:
    result = await db.execute(
        select(AdvertisementAsset)
        .options(selectinload(AdvertisementAsset.renditions))
        .where(
            AdvertisementAsset.status == AssetStatus.READY,
            AdvertisementAsset.moderation_status == AssetModerationStatus.PENDING,
        )
        .order_by(AdvertisementAsset.created_at.asc())
    )
    return list(result.scalars().all())


async def get_asset_for_admin(db: AsyncSession, asset_id: uuid.UUID) -> AdvertisementAsset:
    result = await db.execute(
        select(AdvertisementAsset)
        .options(selectinload(AdvertisementAsset.renditions))
        .where(AdvertisementAsset.id == asset_id)
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset


async def approve_asset(db: AsyncSession, *, asset: AdvertisementAsset, admin_id: uuid.UUID) -> AdvertisementAsset:
    if asset.status != AssetStatus.READY:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asset isn't processed/playable yet")
    if asset.moderation_status == AssetModerationStatus.APPROVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asset is already approved")

    asset.moderation_status = AssetModerationStatus.APPROVED
    asset.moderation_note = None
    asset.moderated_by_admin_id = admin_id
    asset.moderated_at = datetime.now(timezone.utc)
    # No db.refresh() here: it would expire every attribute including the
    # eager-loaded `renditions` relationship, and re-accessing it below (in
    # _asset_to_read) would trigger an implicit lazy-load — unsupported under
    # AsyncSession (MissingGreenlet). Every field the caller needs was already
    # set above in Python, so there's nothing server-side left to re-read.
    await db.commit()

    if asset.asset_type.value in _NOTIFIABLE_ASSET_TYPES:
        await _notify_influencers_of_approved_media(db, asset=asset)

    return asset


async def reject_asset(
    db: AsyncSession, *, asset: AdvertisementAsset, admin_id: uuid.UUID, reason: str
) -> AdvertisementAsset:
    if asset.moderation_status == AssetModerationStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Asset is already approved and shared with influencers"
        )

    asset.moderation_status = AssetModerationStatus.REJECTED
    asset.moderation_note = reason
    asset.moderated_by_admin_id = admin_id
    asset.moderated_at = datetime.now(timezone.utc)
    await db.commit()
    return asset


async def _notify_influencers_of_approved_media(db: AsyncSession, *, asset: AdvertisementAsset) -> None:
    advertisement = await db.get(Advertisement, asset.advertisement_id)
    brand = await db.get(Brand, advertisement.brand_id) if advertisement else None
    brand_name = brand.business_name if brand else "A brand"
    await notify_all_influencers(
        db,
        type_=NotificationType.NEW_BRAND_MEDIA,
        title=f"{brand_name} shared new {asset.asset_type.value} content",
        body=f'New {asset.asset_type.value} added to "{advertisement.title if advertisement else "an advertisement"}" '
        f"— see what {brand_name} is looking for.",
        link="/influencer/marketplace",
        data={
            "advertisement_id": str(asset.advertisement_id),
            "asset_id": str(asset.id),
            "asset_type": asset.asset_type.value,
            "brand_name": brand_name,
        },
    )
