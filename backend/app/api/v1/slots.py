import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool

from app.core.db import get_db
from app.core.deps import require_influencer
from app.models.advertisement import Advertisement
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.campaign_creative import CampaignCreative
from app.models.campaign_slot import CampaignSlot
from app.models.comment import Comment
from app.models.enums import NativePostVisibility, SlotStatus
from app.models.post_metric_snapshot import PostMetricSnapshot
from app.models.social_account import SocialAccount
from app.models.social_post import SocialPost
from app.models.social_feed import NativePost, NativePostMedia
from app.models.user import User
from app.schemas.campaign_slot import CampaignSlotRead, MySlotRead
from app.schemas.campaign_creative import CampaignCreativePublicationRead, CampaignCreativeRead, PublishCampaignCreativeRequest
from app.schemas.comment import CommentRead
from app.schemas.social_post import CreatePostRequest, PostMetricSnapshotRead, SocialPostRead, SubmitPostUrlRequest
from app.services.slot_claim import claim_slot
from app.services.social_comments import poll_post_comments
from app.services.social_metrics import poll_post_metrics
from app.services.social_posting import create_post_for_slot, submit_manual_post_url
from app.services.malware_scanning import scan_upload
from app.services.storage import get_storage_backend, read_with_limit, validate_media_signature
from app.services.video_processing import VideoProcessingError, probe_video

router = APIRouter(prefix="/slots", tags=["slots"], dependencies=[Depends(require_influencer)])


async def _get_own_slot(db: AsyncSession, user: User, slot_id: uuid.UUID) -> CampaignSlot:
    result = await db.execute(
        select(CampaignSlot).where(CampaignSlot.id == slot_id, CampaignSlot.influencer_id == user.id)
    )
    slot = result.scalar_one_or_none()
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slot not found")
    return slot


async def _get_own_post(db: AsyncSession, user: User, slot_id: uuid.UUID) -> tuple[CampaignSlot, SocialPost]:
    slot = await _get_own_slot(db, user, slot_id)
    result = await db.execute(select(SocialPost).where(SocialPost.campaign_slot_id == slot.id))
    post = result.scalar_one_or_none()
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This slot has no post yet")
    return slot, post


def _creative_read(creative: CampaignCreative) -> CampaignCreativeRead:
    return CampaignCreativeRead(
        id=creative.id,
        campaign_slot_id=creative.campaign_slot_id,
        influencer_id=creative.influencer_id,
        original_filename=creative.original_filename,
        mime_type=creative.mime_type,
        duration_seconds=creative.duration_seconds,
        native_post_id=creative.native_post_id,
        url=get_storage_backend().url_for(creative.storage_key),
        created_at=creative.created_at,
        updated_at=creative.updated_at,
    )


@router.post("/{slot_id}/claim", response_model=CampaignSlotRead)
async def claim_slot_endpoint(
    slot_id: uuid.UUID, user: User = Depends(require_influencer), db: AsyncSession = Depends(get_db)
) -> CampaignSlotRead:
    slot = await claim_slot(db, slot_id=slot_id, influencer_id=user.id)
    return CampaignSlotRead.model_validate(slot)


@router.get("/mine", response_model=list[MySlotRead])
async def list_my_slots(
    user: User = Depends(require_influencer), db: AsyncSession = Depends(get_db)
) -> list[MySlotRead]:
    stmt = (
        select(CampaignSlot, Campaign, Advertisement, Brand)
        .join(Campaign, CampaignSlot.campaign_id == Campaign.id)
        .join(Advertisement, Campaign.advertisement_id == Advertisement.id)
        .join(Brand, Campaign.brand_id == Brand.id)
        .where(CampaignSlot.influencer_id == user.id)
        .order_by(CampaignSlot.claimed_at.desc())
    )
    rows = (await db.execute(stmt)).all()

    return [
        MySlotRead(
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
            brand_id=brand.id,
            brand_name=brand.business_name,
            advertisement_title=advertisement.title,
        )
        for slot, campaign, advertisement, brand in rows
    ]


@router.get("/{slot_id}/creative", response_model=CampaignCreativeRead)
async def get_slot_creative(
    slot_id: uuid.UUID, user: User = Depends(require_influencer), db: AsyncSession = Depends(get_db)
) -> CampaignCreativeRead:
    slot = await _get_own_slot(db, user, slot_id)
    creative = (
        await db.execute(select(CampaignCreative).where(CampaignCreative.campaign_slot_id == slot.id))
    ).scalar_one_or_none()
    if creative is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No saved creative for this slot")
    return _creative_read(creative)


@router.post("/{slot_id}/creative", response_model=CampaignCreativeRead, status_code=status.HTTP_201_CREATED)
async def save_slot_creative(
    slot_id: uuid.UUID,
    file: UploadFile = File(...),
    user: User = Depends(require_influencer),
    db: AsyncSession = Depends(get_db),
) -> CampaignCreativeRead:
    """Save the influencer's finished native video after server-side checks.

    Browser duration metadata is useful feedback only; ffprobe is the source of
    truth so a crafted upload cannot bypass the 30-second campaign limit.
    """
    slot = await _get_own_slot(db, user, slot_id)
    if slot.status != SlotStatus.CLAIMED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only claimed slots can have a draft creative")

    content_type = file.content_type or ""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in {".mp4", ".mov", ".webm"} or not content_type.startswith("video/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload an MP4, MOV, or WebM video")
    content = await read_with_limit(file, 200 * 1024 * 1024)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty video uploads are not allowed")
    validate_media_signature(media_type="video", content=content)
    scan_upload(content)

    storage = get_storage_backend()
    storage_key = f"campaign-creatives/{slot.id}/{uuid.uuid4()}{ext}"
    storage.save(storage_key, content)
    try:
        probe = await run_in_threadpool(probe_video, storage.local_path(storage_key))
    except VideoProcessingError as exc:
        storage.delete(storage_key)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is not a readable video") from exc
    if probe.duration_seconds <= 0 or probe.duration_seconds > 30:
        storage.delete(storage_key)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Finished campaign videos must be between 1 and 30 seconds")

    existing = (
        await db.execute(select(CampaignCreative).where(CampaignCreative.campaign_slot_id == slot.id))
    ).scalar_one_or_none()
    old_storage_key = existing.storage_key if existing else None
    if existing is None:
        creative = CampaignCreative(
            campaign_slot_id=slot.id,
            influencer_id=user.id,
            storage_key=storage_key,
            original_filename=file.filename or "creative-video",
            mime_type=content_type,
            duration_seconds=probe.duration_seconds,
        )
        db.add(creative)
    else:
        creative = existing
        creative.storage_key = storage_key
        creative.original_filename = file.filename or "creative-video"
        creative.mime_type = content_type
        creative.duration_seconds = probe.duration_seconds
    try:
        await db.commit()
        await db.refresh(creative)
    except Exception:
        await db.rollback()
        storage.delete(storage_key)
        raise
    if old_storage_key and old_storage_key != storage_key:
        storage.delete(old_storage_key)
    return _creative_read(creative)


@router.post("/{slot_id}/creative/publish", response_model=CampaignCreativePublicationRead, status_code=status.HTTP_201_CREATED)
async def publish_slot_creative_to_clout(
    slot_id: uuid.UUID,
    payload: PublishCampaignCreativeRequest,
    user: User = Depends(require_influencer),
    db: AsyncSession = Depends(get_db),
) -> CampaignCreativePublicationRead:
    """Publish a saved campaign creative as a public, playable Clout post.

    This deliberately does not advance the external campaign-post workflow:
    native Clout visibility and delivery to a connected external account are
    different events, and each needs an honest status for brands and creators.
    """
    slot = await _get_own_slot(db, user, slot_id)
    if slot.status != SlotStatus.CLAIMED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only claimed slots can publish a creative")
    creative = (
        await db.execute(select(CampaignCreative).where(CampaignCreative.campaign_slot_id == slot.id))
    ).scalar_one_or_none()
    if creative is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Save a finished campaign creative before publishing")
    if creative.native_post_id:
        post = await db.get(NativePost, creative.native_post_id)
        if post is not None:
            return CampaignCreativePublicationRead(native_post_id=post.id, caption=post.body, feed_path="/social")

    post = NativePost(author_id=user.id, body=payload.caption.strip(), visibility=NativePostVisibility.PUBLIC)
    db.add(post)
    await db.flush()

    storage = get_storage_backend()
    ext = os.path.splitext(creative.original_filename)[1].lower() or ".mp4"
    public_storage_key = f"social-campaigns/{post.id}/video/{uuid.uuid4()}{ext}"
    try:
        source = await run_in_threadpool(storage.read, creative.storage_key)
        await run_in_threadpool(storage.save, public_storage_key, source)
        db.add(
            NativePostMedia(
                post_id=post.id,
                storage_key=public_storage_key,
                mime_type=creative.mime_type,
                media_type="video",
                processing_status="ready",
            )
        )
        creative.native_post_id = post.id
        await db.commit()
    except Exception:
        await db.rollback()
        storage.delete(public_storage_key)
        raise
    return CampaignCreativePublicationRead(native_post_id=post.id, caption=post.body, feed_path="/social")


@router.post("/{slot_id}/post", response_model=SocialPostRead, status_code=status.HTTP_201_CREATED)
async def create_slot_post(
    slot_id: uuid.UUID,
    payload: CreatePostRequest,
    user: User = Depends(require_influencer),
    db: AsyncSession = Depends(get_db),
) -> SocialPostRead:
    slot = await _get_own_slot(db, user, slot_id)

    account_result = await db.execute(
        select(SocialAccount).where(SocialAccount.id == payload.social_account_id, SocialAccount.owner_user_id == user.id)
    )
    social_account = account_result.scalar_one_or_none()
    if social_account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Social account not found")

    post = await create_post_for_slot(db, slot=slot, social_account=social_account, caption=payload.caption)
    return SocialPostRead.model_validate(post)


@router.get("/{slot_id}/post", response_model=SocialPostRead)
async def get_slot_post(
    slot_id: uuid.UUID, user: User = Depends(require_influencer), db: AsyncSession = Depends(get_db)
) -> SocialPostRead:
    _, post = await _get_own_post(db, user, slot_id)
    return SocialPostRead.model_validate(post)


@router.patch("/{slot_id}/post/submit-url", response_model=SocialPostRead)
async def submit_slot_post_url(
    slot_id: uuid.UUID,
    payload: SubmitPostUrlRequest,
    user: User = Depends(require_influencer),
    db: AsyncSession = Depends(get_db),
) -> SocialPostRead:
    slot, post = await _get_own_post(db, user, slot_id)
    post = await submit_manual_post_url(db, post=post, slot=slot, post_url=payload.post_url)
    return SocialPostRead.model_validate(post)


@router.get("/{slot_id}/post/metrics", response_model=list[PostMetricSnapshotRead])
async def get_slot_post_metrics(
    slot_id: uuid.UUID, user: User = Depends(require_influencer), db: AsyncSession = Depends(get_db)
) -> list[PostMetricSnapshotRead]:
    """Polls fresh metrics on every call before returning the series — the same
    on-demand pattern GET /campaigns/{id}/payment uses, so viewing this page
    doesn't require waiting on the scheduled Celery task."""
    _, post = await _get_own_post(db, user, slot_id)
    await poll_post_metrics(db, post=post)

    result = await db.execute(
        select(PostMetricSnapshot)
        .where(PostMetricSnapshot.social_post_id == post.id)
        .order_by(PostMetricSnapshot.fetched_at.asc())
    )
    return [PostMetricSnapshotRead.model_validate(s) for s in result.scalars().all()]


@router.get("/{slot_id}/post/comments", response_model=list[CommentRead])
async def get_slot_post_comments(
    slot_id: uuid.UUID, user: User = Depends(require_influencer), db: AsyncSession = Depends(get_db)
) -> list[CommentRead]:
    """Polls for and classifies new comments on every call before returning
    the list — same on-demand pattern as the metrics endpoint."""
    _, post = await _get_own_post(db, user, slot_id)
    await poll_post_comments(db, post=post)

    result = await db.execute(
        select(Comment)
        .options(selectinload(Comment.analysis))
        .where(Comment.social_post_id == post.id)
        .order_by(Comment.posted_at.asc())
    )
    return [CommentRead.model_validate(c) for c in result.scalars().all()]
