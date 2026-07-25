import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.deps import require_brand
from app.models.advertisement import Advertisement
from app.models.campaign import Campaign
from app.models.enums import AdvertisementStatus, CampaignStatus, WalletOwnerType
from app.models.payment import Payment
from app.models.user import User
from app.models.campaign_report import CampaignReport
from app.schemas.campaign import CampaignCreate, CampaignRead
from app.schemas.campaign_analytics import CampaignAnalyticsRead, CommentSentimentSummaryRead, InfluencerPerformanceRead
from app.schemas.campaign_report import CampaignReportRead
from app.schemas.campaign_slot import CampaignDetailRead
from app.schemas.common import Page
from app.schemas.payment import FundCampaignRequest, PaymentRead
from app.services.campaign_analytics import compute_campaign_analytics
from app.services.campaign_funding import initiate_campaign_funding, sync_payment_status
from app.services.campaign_lifecycle import cancel_campaign
from app.services.campaign_reports import generate_campaign_report
from app.services.comment_summary import compute_comment_summary
from app.services.ledger import get_wallet
from app.services.pricing import price_campaign

router = APIRouter(prefix="/campaigns", tags=["campaigns"], dependencies=[Depends(require_brand)])


class CancelCampaignRequest(BaseModel):
    phone_number: str | None = None


class CampaignFundingResponse(BaseModel):
    campaign: CampaignRead
    payment: PaymentRead


async def _get_owned_campaign(db: AsyncSession, user: User, campaign_id: uuid.UUID) -> Campaign:
    result = await db.execute(
        select(Campaign)
        .options(selectinload(Campaign.slots))
        .where(Campaign.id == campaign_id, Campaign.brand_id == user.id)
    )
    campaign = result.scalar_one_or_none()
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return campaign


async def _to_detail(db: AsyncSession, campaign: Campaign) -> CampaignDetailRead:
    base = CampaignRead.model_validate(campaign).model_dump()
    escrow_balance = None
    try:
        escrow_wallet = await get_wallet(
            db, owner_type=WalletOwnerType.ESCROW, owner_id=campaign.id, currency=campaign.currency
        )
        escrow_balance = escrow_wallet.balance
    except RuntimeError:
        pass
    return CampaignDetailRead(**base, slots=campaign.slots, escrow_balance=escrow_balance)


@router.post("", response_model=CampaignRead, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    payload: CampaignCreate, user: User = Depends(require_brand), db: AsyncSession = Depends(get_db)
) -> CampaignRead:
    ad_result = await db.execute(
        select(Advertisement).where(Advertisement.id == payload.advertisement_id, Advertisement.brand_id == user.id)
    )
    advertisement = ad_result.scalar_one_or_none()
    if advertisement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Advertisement not found")
    if advertisement.status != AdvertisementStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Advertisement must be 'ready' (a processed video asset) before it can be used in a campaign",
        )

    pricing = await price_campaign(db, platforms=payload.platforms, target_views=payload.target_views)

    campaign = Campaign(
        brand_id=user.id,
        advertisement_id=advertisement.id,
        status=CampaignStatus.PENDING_FUNDING,
        platforms=[p.value for p in payload.platforms],
        target_views=payload.target_views,
        tier=payload.tier,
        slot_count=payload.slot_count,
        performance_window_days=payload.performance_window_days,
        target_sector=payload.target_sector,
        target_location=payload.target_location,
        rate_snapshot=pricing.rate_snapshot,
        brand_fee_pct=pricing.brand_fee_pct,
        base_price=pricing.base_price,
        total_brand_payment=pricing.total_brand_payment,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return CampaignRead.model_validate(campaign)


@router.get("", response_model=Page[CampaignRead])
async def list_campaigns(
    user: User = Depends(require_brand),
    db: AsyncSession = Depends(get_db),
    status_filter: CampaignStatus | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> Page[CampaignRead]:
    stmt = select(Campaign).where(Campaign.brand_id == user.id)
    count_stmt = select(func.count()).select_from(Campaign).where(Campaign.brand_id == user.id)

    if status_filter is not None:
        stmt = stmt.where(Campaign.status == status_filter)
        count_stmt = count_stmt.where(Campaign.status == status_filter)

    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(Campaign.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    items = (await db.execute(stmt)).scalars().all()

    return Page(items=[CampaignRead.model_validate(c) for c in items], total=total, page=page, page_size=page_size)


@router.get("/{campaign_id}", response_model=CampaignDetailRead)
async def get_campaign(
    campaign_id: uuid.UUID, user: User = Depends(require_brand), db: AsyncSession = Depends(get_db)
) -> CampaignDetailRead:
    campaign = await _get_owned_campaign(db, user, campaign_id)
    return await _to_detail(db, campaign)


@router.post("/{campaign_id}/fund", response_model=CampaignFundingResponse)
async def fund_campaign(
    campaign_id: uuid.UUID,
    payload: FundCampaignRequest,
    user: User = Depends(require_brand),
    db: AsyncSession = Depends(get_db),
) -> CampaignFundingResponse:
    """Initiates a MoMo request-to-pay for the campaign total. This does NOT
    immediately fund escrow or create slots — MoMo Collections are asynchronous,
    so the campaign sits in PENDING_FUNDING until the provider confirms via
    webhook (POST /webhooks/momo/collection) or the brand/reconciliation polls
    GET /campaigns/{id}/payment.
    """
    campaign = await _get_owned_campaign(db, user, campaign_id)
    payment = await initiate_campaign_funding(db, campaign=campaign, phone_number=payload.phone_number)
    campaign = await _get_owned_campaign(db, user, campaign_id)
    return CampaignFundingResponse(campaign=CampaignRead.model_validate(campaign), payment=PaymentRead.model_validate(payment))


@router.get("/{campaign_id}/payment", response_model=PaymentRead)
async def get_campaign_payment(
    campaign_id: uuid.UUID, user: User = Depends(require_brand), db: AsyncSession = Depends(get_db)
) -> PaymentRead:
    """Polls the payment provider directly if the latest Payment is still
    PENDING — covers a brand checking status when a webhook hasn't arrived yet
    (the same gap the reconciliation Celery task closes on a schedule)."""
    campaign = await _get_owned_campaign(db, user, campaign_id)
    result = await db.execute(
        select(Payment).where(Payment.campaign_id == campaign.id).order_by(Payment.created_at.desc())
    )
    payment = result.scalars().first()
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No payment has been initiated for this campaign")

    payment = await sync_payment_status(db, payment=payment)
    return PaymentRead.model_validate(payment)


@router.get("/{campaign_id}/analytics", response_model=CampaignAnalyticsRead)
async def get_campaign_analytics(
    campaign_id: uuid.UUID, user: User = Depends(require_brand), db: AsyncSession = Depends(get_db)
) -> CampaignAnalyticsRead:
    """Every figure here is aggregated straight from tracked slot/post/metric
    data — nothing estimated. Phase 7's AI report generator narrates these same
    numbers rather than computing or inventing its own."""
    campaign = await _get_owned_campaign(db, user, campaign_id)
    analytics = await compute_campaign_analytics(db, campaign_id=campaign.id)
    comment_summary = await compute_comment_summary(db, campaign_id=campaign.id)
    return CampaignAnalyticsRead(
        total_target_views=analytics.total_target_views,
        total_verified_views=analytics.total_verified_views,
        progress_pct=analytics.progress_pct,
        total_engagement=analytics.total_engagement,
        views_by_platform=analytics.views_by_platform,
        engagement_by_platform=analytics.engagement_by_platform,
        influencer_performance=[
            InfluencerPerformanceRead(
                influencer_id=p.influencer_id,
                username=p.username,
                platform=p.platform,
                views=p.views,
                likes=p.likes,
                comments=p.comments,
                shares=p.shares,
            )
            for p in analytics.influencer_performance
        ],
        top_influencer_username=analytics.top_influencer_username,
        top_platform=analytics.top_platform,
        slot_status_counts=analytics.slot_status_counts,
        comment_summary=CommentSentimentSummaryRead(
            total_comments=comment_summary.total_comments,
            category_counts=comment_summary.category_counts,
            average_sentiment_score=comment_summary.average_sentiment_score,
            sample_questions=comment_summary.sample_questions,
        ),
    )


@router.post("/{campaign_id}/report", response_model=CampaignReportRead, status_code=status.HTTP_201_CREATED)
async def create_campaign_report(
    campaign_id: uuid.UUID, user: User = Depends(require_brand), db: AsyncSession = Depends(get_db)
) -> CampaignReportRead:
    """Generates a new report (never overwrites a prior one — see
    services/campaign_reports.py). Every number in the narrative is either
    interpolated directly (template mode) or has passed the fabrication
    guardrail (Anthropic mode, falling back to template on failure)."""
    campaign = await _get_owned_campaign(db, user, campaign_id)
    report = await generate_campaign_report(db, campaign=campaign)
    return CampaignReportRead.model_validate(report)


@router.get("/{campaign_id}/report", response_model=CampaignReportRead)
async def get_latest_campaign_report(
    campaign_id: uuid.UUID, user: User = Depends(require_brand), db: AsyncSession = Depends(get_db)
) -> CampaignReportRead:
    campaign = await _get_owned_campaign(db, user, campaign_id)
    result = await db.execute(
        select(CampaignReport).where(CampaignReport.campaign_id == campaign.id).order_by(CampaignReport.created_at.desc())
    )
    report = result.scalars().first()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No report has been generated for this campaign yet")
    return CampaignReportRead.model_validate(report)


@router.post("/{campaign_id}/cancel", response_model=CampaignDetailRead)
async def cancel_campaign_endpoint(
    campaign_id: uuid.UUID,
    payload: CancelCampaignRequest = CancelCampaignRequest(),
    user: User = Depends(require_brand),
    db: AsyncSession = Depends(get_db),
) -> CampaignDetailRead:
    campaign = await _get_owned_campaign(db, user, campaign_id)
    campaign = await cancel_campaign(db, campaign, refund_phone_number=payload.phone_number)
    return await _to_detail(db, campaign)
