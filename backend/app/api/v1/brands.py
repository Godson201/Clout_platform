import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user, require_brand
from app.models.brand import Brand
from app.models.enums import WalletOwnerType
from app.models.user import User
from app.schemas.brand import BrandRead, BrandUpdate
from app.schemas.brand_dashboard import BrandDashboardSummaryRead, DailyViewsRead, TopCampaignRead
from app.schemas.public_profile import PublicBrandProfile
from app.schemas.wallet import WalletRead
from app.services.audit import write_audit_log
from app.services.brand_dashboard import compute_brand_dashboard_summary
from app.services.ledger import get_wallet
from app.services.profile_pictures import store_profile_picture
from app.services.public_profiles import build_public_brand_profile

router = APIRouter(prefix="/brands", tags=["brands"])


async def _get_own_brand(db: AsyncSession, user: User) -> Brand:
    result = await db.execute(select(Brand).where(Brand.id == user.id))
    brand = result.scalar_one_or_none()
    if brand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand profile not found")
    return brand


@router.get("/me", response_model=BrandRead)
async def get_my_brand(user: User = Depends(require_brand), db: AsyncSession = Depends(get_db)) -> BrandRead:
    brand = await _get_own_brand(db, user)
    return BrandRead.model_validate(brand)


@router.patch("/me", response_model=BrandRead)
async def update_my_brand(
    payload: BrandUpdate, user: User = Depends(require_brand), db: AsyncSession = Depends(get_db)
) -> BrandRead:
    brand = await _get_own_brand(db, user)
    before = BrandRead.model_validate(brand).model_dump(mode="json")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(brand, field, value)

    await write_audit_log(
        db,
        actor_user_id=user.id,
        action="brand.update",
        entity_type="brand",
        entity_id=brand.id,
        before=before,
        after=BrandRead.model_validate(brand).model_dump(mode="json"),
    )

    await db.commit()
    await db.refresh(brand)
    return BrandRead.model_validate(brand)


@router.post("/me/logo", response_model=BrandRead)
async def upload_my_logo(
    file: UploadFile, user: User = Depends(require_brand), db: AsyncSession = Depends(get_db)
) -> BrandRead:
    brand = await _get_own_brand(db, user)
    brand.logo_url = await store_profile_picture(owner_kind="brands", owner_id=user.id, file=file)
    await db.commit()
    await db.refresh(brand)
    return BrandRead.model_validate(brand)


@router.get("/me/wallet", response_model=WalletRead)
async def get_my_wallet(user: User = Depends(require_brand), db: AsyncSession = Depends(get_db)) -> WalletRead:
    wallet = await get_wallet(db, owner_type=WalletOwnerType.BRAND, owner_id=user.id)
    return WalletRead.model_validate(wallet)


@router.get("/me/dashboard-summary", response_model=BrandDashboardSummaryRead)
async def get_my_dashboard_summary(
    user: User = Depends(require_brand), db: AsyncSession = Depends(get_db)
) -> BrandDashboardSummaryRead:
    """Every figure is aggregated straight from tracked campaign/slot/post/metric/
    payment data — nothing estimated or fabricated, same principle as the
    per-campaign analytics endpoint."""
    summary = await compute_brand_dashboard_summary(db, brand_id=user.id)
    return BrandDashboardSummaryRead(
        total_campaigns=summary.total_campaigns,
        total_campaigns_mom_pct=summary.total_campaigns_mom_pct,
        total_views=summary.total_views,
        total_views_mom_pct=summary.total_views_mom_pct,
        total_engagement=summary.total_engagement,
        total_engagement_mom_pct=summary.total_engagement_mom_pct,
        total_spent=summary.total_spent,
        total_spent_mom_pct=summary.total_spent_mom_pct,
        currency=summary.currency,
        views_over_time=[DailyViewsRead(day=d.day, views=d.views) for d in summary.views_over_time],
        views_by_platform=summary.views_by_platform,
        top_campaigns=[
            TopCampaignRead(
                campaign_id=c.campaign_id,
                title=c.title,
                platforms=c.platforms,
                influencer_avatars=c.influencer_avatars,
                total_views=c.total_views,
                progress_pct=c.progress_pct,
                status=c.status,
            )
            for c in summary.top_campaigns
        ],
    )


@router.get("/{brand_id}/public", response_model=PublicBrandProfile)
async def get_public_brand_profile(
    brand_id: uuid.UUID, _: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> PublicBrandProfile:
    brand = await db.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    return await build_public_brand_profile(db, brand)
