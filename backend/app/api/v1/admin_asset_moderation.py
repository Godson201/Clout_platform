import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_admin
from app.models.advertisement import Advertisement
from app.models.advertisement_asset import AdvertisementAsset
from app.models.brand import Brand
from app.models.user import User
from app.schemas.advertisement import (
    AdvertisementAssetRead,
    AdvertisementRenditionRead,
    AssetModerationQueueItem,
    RejectAssetRequest,
)
from app.services.asset_moderation import (
    approve_asset,
    get_asset_for_admin,
    list_assets_pending_review,
    reject_asset,
)
from app.services.storage import get_storage_backend

router = APIRouter(prefix="/admin/asset-moderation", tags=["admin"], dependencies=[Depends(require_admin)])


def _asset_to_read(asset: AdvertisementAsset) -> AdvertisementAssetRead:
    storage = get_storage_backend()
    return AdvertisementAssetRead(
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
        moderation_note=asset.moderation_note,
        distribution=asset.distribution,
        # Recipient identities are private to the brand; admins only need the
        # selected distribution mode to review the asset.
        recipient_influencer_ids=[],
        renditions=[
            AdvertisementRenditionRead(
                id=r.id,
                platform=r.platform,
                status=r.status,
                width=r.width,
                height=r.height,
                duration_seconds=r.duration_seconds,
                error_message=r.error_message,
                url=storage.url_for(r.storage_key) if r.storage_key else None,
            )
            for r in asset.renditions
        ],
    )


@router.get("", response_model=list[AssetModerationQueueItem])
async def list_pending_media(db: AsyncSession = Depends(get_db)) -> list[AssetModerationQueueItem]:
    assets = await list_assets_pending_review(db)
    items: list[AssetModerationQueueItem] = []
    for asset in assets:
        advertisement = await db.get(Advertisement, asset.advertisement_id)
        brand = await db.get(Brand, advertisement.brand_id) if advertisement else None
        items.append(
            AssetModerationQueueItem(
                **_asset_to_read(asset).model_dump(),
                advertisement_id=asset.advertisement_id,
                advertisement_title=advertisement.title if advertisement else "Unknown",
                brand_name=brand.business_name if brand else "Unknown",
            )
        )
    return items


@router.post("/{asset_id}/approve", response_model=AdvertisementAssetRead)
async def approve_media(
    asset_id: uuid.UUID, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> AdvertisementAssetRead:
    asset = await get_asset_for_admin(db, asset_id)
    asset = await approve_asset(db, asset=asset, admin_id=admin.id)
    return _asset_to_read(asset)


@router.post("/{asset_id}/reject", response_model=AdvertisementAssetRead)
async def reject_media(
    asset_id: uuid.UUID,
    payload: RejectAssetRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdvertisementAssetRead:
    asset = await get_asset_for_admin(db, asset_id)
    asset = await reject_asset(db, asset=asset, admin_id=admin.id, reason=payload.reason)
    return _asset_to_read(asset)
