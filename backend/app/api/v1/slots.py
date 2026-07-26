import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.deps import require_influencer
from app.models.advertisement import Advertisement
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.campaign_slot import CampaignSlot
from app.models.comment import Comment
from app.models.post_metric_snapshot import PostMetricSnapshot
from app.models.social_account import SocialAccount
from app.models.social_post import SocialPost
from app.models.user import User
from app.schemas.campaign_slot import CampaignSlotRead, MySlotRead
from app.schemas.comment import CommentRead
from app.schemas.social_post import CreatePostRequest, PostMetricSnapshotRead, SocialPostRead, SubmitPostUrlRequest
from app.services.slot_claim import claim_slot
from app.services.social_comments import poll_post_comments
from app.services.social_metrics import poll_post_metrics
from app.services.social_posting import create_post_for_slot, submit_manual_post_url

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
