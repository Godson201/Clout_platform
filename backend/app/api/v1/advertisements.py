import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.deps import require_brand
from app.models.advertisement import Advertisement
from app.models.advertisement_asset import AdvertisementAsset, AssetShareRecipient
from app.models.advertisement_template import AdvertisementTemplate
from app.models.enums import AdvertisementStatus, AssetDistribution, AssetModerationStatus, AssetStatus, AssetType, UserType
from app.models.influencer import Influencer
from app.models.user import User
from app.schemas.advertisement import (
    AdvertisementAssetRead,
    AssetDistributionUpdate,
    AdvertisementCreate,
    AdvertisementDetailRead,
    AdvertisementRead,
    AdvertisementRenditionRead,
    AdvertisementUpdate,
    InfluencerAudienceOption,
)
from app.schemas.common import Page
from app.services.advertisement_assets import delete_advertisement_asset, store_advertisement_asset
from app.services.storage import get_storage_backend

router = APIRouter(prefix="/advertisements", tags=["advertisements"], dependencies=[Depends(require_brand)])


async def _get_owned_advertisement(db: AsyncSession, user: User, advertisement_id: uuid.UUID) -> Advertisement:
    result = await db.execute(
        select(Advertisement)
        .options(
            selectinload(Advertisement.assets).selectinload(AdvertisementAsset.renditions),
            selectinload(Advertisement.assets).selectinload(AdvertisementAsset.recipients),
        )
        .where(Advertisement.id == advertisement_id, Advertisement.brand_id == user.id)
    )
    advertisement = result.scalar_one_or_none()
    if advertisement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Advertisement not found")
    return advertisement


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
        recipient_influencer_ids=[recipient.influencer_id for recipient in asset.recipients],
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


def _advertisement_to_detail(advertisement: Advertisement) -> AdvertisementDetailRead:
    base = AdvertisementRead.model_validate(advertisement).model_dump()
    return AdvertisementDetailRead(**base, assets=[_asset_to_read(a) for a in advertisement.assets])


async def _get_owned_asset(
    db: AsyncSession, *, user: User, advertisement_id: uuid.UUID, asset_id: uuid.UUID
) -> AdvertisementAsset:
    result = await db.execute(
        select(AdvertisementAsset)
        .join(Advertisement, AdvertisementAsset.advertisement_id == Advertisement.id)
        .options(selectinload(AdvertisementAsset.recipients))
        .where(AdvertisementAsset.id == asset_id, Advertisement.id == advertisement_id, Advertisement.brand_id == user.id)
    )
    asset = result.scalar_one_or_none()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset


@router.post("", response_model=AdvertisementRead, status_code=status.HTTP_201_CREATED)
async def create_advertisement(
    payload: AdvertisementCreate, user: User = Depends(require_brand), db: AsyncSession = Depends(get_db)
) -> AdvertisementRead:
    template = await db.get(AdvertisementTemplate, payload.template_id)
    if template is None or not template.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Template not found or inactive")

    advertisement = Advertisement(
        brand_id=user.id,
        template_id=template.id,
        title=payload.title,
        script_text=payload.script_text,
        cta_text=payload.cta_text,
        hashtags=payload.hashtags,
        duration_seconds=payload.duration_seconds or template.default_duration_seconds,
    )
    db.add(advertisement)
    await db.commit()
    await db.refresh(advertisement)
    return AdvertisementRead.model_validate(advertisement)


@router.get("", response_model=Page[AdvertisementRead])
async def list_advertisements(
    user: User = Depends(require_brand),
    db: AsyncSession = Depends(get_db),
    status_filter: AdvertisementStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[AdvertisementRead]:
    stmt = select(Advertisement).where(Advertisement.brand_id == user.id)
    count_stmt = select(func.count()).select_from(Advertisement).where(Advertisement.brand_id == user.id)

    if status_filter is not None:
        stmt = stmt.where(Advertisement.status == status_filter)
        count_stmt = count_stmt.where(Advertisement.status == status_filter)

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(Advertisement.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(stmt)).scalars().all()

    return Page(
        items=[AdvertisementRead.model_validate(a) for a in items], total=total, page=page, page_size=page_size
    )


@router.get("/{advertisement_id}", response_model=AdvertisementDetailRead)
async def get_advertisement(
    advertisement_id: uuid.UUID, user: User = Depends(require_brand), db: AsyncSession = Depends(get_db)
) -> AdvertisementDetailRead:
    advertisement = await _get_owned_advertisement(db, user, advertisement_id)
    return _advertisement_to_detail(advertisement)


@router.patch("/{advertisement_id}", response_model=AdvertisementDetailRead)
async def update_advertisement(
    advertisement_id: uuid.UUID,
    payload: AdvertisementUpdate,
    user: User = Depends(require_brand),
    db: AsyncSession = Depends(get_db),
) -> AdvertisementDetailRead:
    advertisement = await _get_owned_advertisement(db, user, advertisement_id)

    if advertisement.status == AdvertisementStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archived advertisements are read-only")

    updates = payload.model_dump(exclude_unset=True)
    new_status = updates.get("status")
    if new_status == AdvertisementStatus.READY:
        has_ready_video = any(a.asset_type == AssetType.VIDEO and a.status == AssetStatus.READY for a in advertisement.assets)
        if not has_ready_video:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot mark ready: no successfully processed video asset yet",
            )

    for field, value in updates.items():
        setattr(advertisement, field, value)

    await db.commit()

    # Re-fetch fresh rather than db.refresh()-ing in place: refresh() expires
    # *every* attribute on the instance first and only reloads the ones named
    # in attribute_names, so anything left out (e.g. `updated_at`, populated by
    # the server-side onupdate default we just triggered) would come back
    # expired and trigger an implicit lazy-load on next access — raising
    # MissingGreenlet under AsyncSession (same bug class as Phase 1's seed
    # script fix). A plain re-query is simpler than juggling attribute_names.
    advertisement = await _get_owned_advertisement(db, user, advertisement_id)
    return _advertisement_to_detail(advertisement)


@router.post("/{advertisement_id}/assets", response_model=AdvertisementAssetRead, status_code=status.HTTP_201_CREATED)
async def upload_advertisement_asset(
    advertisement_id: uuid.UUID,
    asset_type: AssetType = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(require_brand),
    db: AsyncSession = Depends(get_db),
) -> AdvertisementAssetRead:
    advertisement = await _get_owned_advertisement(db, user, advertisement_id)
    if advertisement.status == AdvertisementStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archived advertisements are read-only")

    asset = await store_advertisement_asset(db, advertisement_id=advertisement.id, asset_type=asset_type, file=file)

    # Video assets are fully transcoded synchronously by the time this returns
    # (eager Celery mode dispatched via run_in_threadpool inside
    # store_advertisement_asset) — but that happened through a separate sync
    # session/connection, so this request's async session has stale in-memory
    # copies of `asset` and its `renditions` (both were created via this same
    # session earlier in the request, so they're sitting in its identity map).
    # populate_existing=True forces a full overwrite from the just-committed
    # rows instead of silently returning the pre-processing in-memory state.
    result = await db.execute(
        select(AdvertisementAsset)
        .options(selectinload(AdvertisementAsset.renditions), selectinload(AdvertisementAsset.recipients))
        .where(AdvertisementAsset.id == asset.id)
        .execution_options(populate_existing=True)
    )
    asset = result.scalar_one()
    return _asset_to_read(asset)


@router.get("/{advertisement_id}/influencer-audience", response_model=list[InfluencerAudienceOption])
async def list_influencer_audience(
    advertisement_id: uuid.UUID,
    query: str | None = Query(default=None, min_length=1, max_length=64),
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(require_brand),
    db: AsyncSession = Depends(get_db),
) -> list[InfluencerAudienceOption]:
    """A minimal, brand-safe directory used only to select explicit recipients."""
    await _get_owned_advertisement(db, user, advertisement_id)
    stmt = (
        select(Influencer)
        .join(User, Influencer.id == User.id)
        .where(User.user_type == UserType.INFLUENCER, User.is_active.is_(True))
        .order_by(Influencer.display_name.asc())
        .limit(limit)
    )
    if query:
        needle = f"%{query.strip()}%"
        stmt = stmt.where(or_(Influencer.display_name.ilike(needle), Influencer.username.ilike(needle)))
    influencers = (await db.execute(stmt)).scalars().all()
    return [
        InfluencerAudienceOption(
            id=influencer.id,
            display_name=influencer.display_name,
            username=influencer.username,
            sector=influencer.sector,
            location=influencer.location,
            follower_tier=influencer.follower_tier.value if influencer.follower_tier else None,
        )
        for influencer in influencers
    ]


@router.patch("/{advertisement_id}/assets/{asset_id}/distribution", response_model=AdvertisementAssetRead)
async def update_asset_distribution(
    advertisement_id: uuid.UUID,
    asset_id: uuid.UUID,
    payload: AssetDistributionUpdate,
    user: User = Depends(require_brand),
    db: AsyncSession = Depends(get_db),
) -> AdvertisementAssetRead:
    """Choose an audience while the asset is still awaiting moderation.

    Changing it after approval would make prior broadcasts impossible to retract,
    so the brand must make this decision before publish/review approval.
    """
    asset = await _get_owned_asset(db, user=user, advertisement_id=advertisement_id, asset_id=asset_id)
    if asset.moderation_status != AssetModerationStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Distribution can only be changed before approval")
    recipient_ids = set(payload.recipient_influencer_ids)
    if payload.distribution == AssetDistribution.SPECIFIC_INFLUENCERS and not recipient_ids:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Select at least one influencer")
    if payload.distribution != AssetDistribution.SPECIFIC_INFLUENCERS and recipient_ids:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Recipients are only valid for specific influencers")

    if recipient_ids:
        valid_ids = set(
            (await db.execute(select(Influencer.id).where(Influencer.id.in_(recipient_ids)))).scalars().all()
        )
        if valid_ids != recipient_ids:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="One or more selected influencers do not exist")

    asset.distribution = payload.distribution
    for recipient in list(asset.recipients):
        await db.delete(recipient)
    if payload.distribution == AssetDistribution.SPECIFIC_INFLUENCERS:
        asset.recipients = [AssetShareRecipient(influencer_id=influencer_id) for influencer_id in recipient_ids]
    await db.commit()
    asset = await _get_owned_asset(db, user=user, advertisement_id=advertisement_id, asset_id=asset_id)
    return _asset_to_read(asset)


@router.delete("/{advertisement_id}/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    advertisement_id: uuid.UUID,
    asset_id: uuid.UUID,
    user: User = Depends(require_brand),
    db: AsyncSession = Depends(get_db),
) -> None:
    advertisement = await _get_owned_advertisement(db, user, advertisement_id)
    asset = next((a for a in advertisement.assets if a.id == asset_id), None)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    delete_advertisement_asset(asset)
    await db.delete(asset)
    await db.commit()
