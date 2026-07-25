from decimal import Decimal

from app.core.db import AsyncSessionLocal
from app.models.enums import SocialPlatform
from app.services.pricing import price_campaign


class TestPricing:
    async def test_single_platform_matches_spec_example(self):
        # Mirrors the product spec's worked example almost exactly: 100,000
        # target views at a per-view rate, 10% brand-side fee on top.
        async with AsyncSessionLocal() as db:
            pricing = await price_campaign(db, platforms=[SocialPlatform.TIKTOK], target_views=100_000)

        assert pricing.base_price == Decimal("100000") * Decimal("5.0000")
        assert pricing.base_price == Decimal("500000.0000")
        assert pricing.brand_fee_pct == Decimal("0.1000")
        assert pricing.total_brand_payment == Decimal("550000.00000")

    async def test_multi_platform_sums_per_platform_targets(self):
        # target_views applies PER platform (Phase 3 modeling decision) — two
        # platforms means the brand is buying target_views worth of reach on
        # *each*, not splitting one pool between them.
        async with AsyncSessionLocal() as db:
            pricing = await price_campaign(
                db, platforms=[SocialPlatform.TIKTOK, SocialPlatform.INSTAGRAM], target_views=10_000
            )

        expected_base = Decimal("10000") * Decimal("5.0000") + Decimal("10000") * Decimal("6.0000")
        assert pricing.base_price == expected_base
        assert set(pricing.rate_snapshot.keys()) == {"tiktok", "instagram"}

    async def test_missing_view_rate_rejected(self):
        from fastapi import HTTPException

        async with AsyncSessionLocal() as db:
            from app.models.view_rate import ViewRate
            from sqlalchemy import delete

            await db.execute(delete(ViewRate).where(ViewRate.platform == SocialPlatform.YOUTUBE))
            await db.commit()

            try:
                await price_campaign(db, platforms=[SocialPlatform.YOUTUBE], target_views=1000)
                assert False, "expected HTTPException"
            except HTTPException as exc:
                assert exc.status_code == 400
