from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import SocialPlatform
from app.models.fee_config import FeeConfig
from app.models.view_rate import ViewRate


async def get_current_fee_config(db: AsyncSession) -> FeeConfig:
    result = await db.execute(select(FeeConfig).order_by(FeeConfig.created_at.desc()))
    config = result.scalars().first()
    if config is None:
        raise RuntimeError("No fee_configs row found — run `python -m app.seeds.seed` first.")
    return config


async def get_view_rates(db: AsyncSession, platforms: list[SocialPlatform]) -> dict[SocialPlatform, Decimal]:
    result = await db.execute(select(ViewRate).where(ViewRate.platform.in_(platforms)))
    rates = {r.platform: Decimal(str(r.rate_per_view)) for r in result.scalars().all()}

    missing = set(platforms) - set(rates)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No configured view rate for: {', '.join(p.value for p in missing)}",
        )
    return rates


class CampaignPricing:
    def __init__(
        self,
        *,
        rate_snapshot: dict[str, str],
        brand_fee_pct: Decimal,
        base_price: Decimal,
        total_brand_payment: Decimal,
    ):
        self.rate_snapshot = rate_snapshot
        self.brand_fee_pct = brand_fee_pct
        self.base_price = base_price
        self.total_brand_payment = total_brand_payment


async def price_campaign(db: AsyncSession, *, platforms: list[SocialPlatform], target_views: int) -> CampaignPricing:
    """base_price = target_views * rate, summed per platform (target_views applies
    PER platform — see Campaign model docstring). total_brand_payment adds the
    brand-side platform fee on top, per the confirmed blended-fee business decision.
    """
    rates = await get_view_rates(db, platforms)
    fee_config = await get_current_fee_config(db)

    base_price = sum((Decimal(target_views) * rates[p] for p in platforms), start=Decimal(0))
    brand_fee_pct = Decimal(str(fee_config.brand_fee_pct))
    total_brand_payment = base_price * (Decimal(1) + brand_fee_pct)

    return CampaignPricing(
        rate_snapshot={p.value: str(rates[p]) for p in platforms},
        brand_fee_pct=brand_fee_pct,
        base_price=base_price,
        total_brand_payment=total_brand_payment,
    )
