from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign import Campaign
from app.models.campaign_slot import CampaignSlot
from app.models.enums import FollowerTier, SocialPlatform

# How far a historical-performance signal is allowed to move the final score —
# deliberately narrow: this is a statistical nudge on top of the explainable
# rule-based score (services/matching.py), not a replacement for it. A real
# learned ranking model (the eventual direction called for once there's enough
# labeled campaign-outcome data to train one) would earn a wider range; a
# frequentist average over what's still a small sample shouldn't be trusted
# that much.
MIN_BOOST = 0.85
MAX_BOOST = 1.15

# Below this many settled slots for a given (sector, platform, tier)
# combination, there isn't enough signal to trust its historical average over
# the platform-wide baseline — return a neutral 1.0 multiplier instead of
# overfitting to two or three data points.
MIN_SAMPLE_SIZE = 5


@dataclass(frozen=True)
class HistoricalPerformance:
    sample_size: int
    segment_average_delivered_pct: float | None
    baseline_average_delivered_pct: float | None
    boost: float


async def _average_delivered_pct(
    db: AsyncSession, *, sector: str, platform: SocialPlatform, tier: FollowerTier
) -> tuple[float | None, int]:
    stmt = (
        select(CampaignSlot.delivered_pct)
        .join(Campaign, CampaignSlot.campaign_id == Campaign.id)
        .where(
            CampaignSlot.delivered_pct.isnot(None),
            CampaignSlot.platform == platform,
            CampaignSlot.tier == tier,
            Campaign.target_sector == sector,
        )
    )
    values = [float(v) for v in (await db.execute(stmt)).scalars().all()]
    if not values:
        return None, 0
    return sum(values) / len(values), len(values)


async def get_historical_performance_boost(
    db: AsyncSession, *, sector: str | None, platform: SocialPlatform, tier: FollowerTier
) -> HistoricalPerformance:
    """A lightweight, frequentist stand-in for "ML recommendations" — there
    still isn't real production volume to train an actual model against, so
    this computes a simple relative signal (does this sector+platform+tier
    combination historically deliver above or below the platform-wide
    average?) instead of fitting one, behind the same function shape a real
    trained model would have so it can be swapped in later without touching
    marketplace.py.
    """
    if sector is None:
        return HistoricalPerformance(
            sample_size=0, segment_average_delivered_pct=None, baseline_average_delivered_pct=None, boost=1.0
        )

    segment_avg, sample_size = await _average_delivered_pct(db, sector=sector, platform=platform, tier=tier)
    if segment_avg is None or sample_size < MIN_SAMPLE_SIZE:
        return HistoricalPerformance(
            sample_size=sample_size,
            segment_average_delivered_pct=segment_avg,
            baseline_average_delivered_pct=None,
            boost=1.0,
        )

    baseline_result = await db.execute(select(CampaignSlot.delivered_pct).where(CampaignSlot.delivered_pct.isnot(None)))
    baseline_values = [float(v) for v in baseline_result.scalars().all()]
    baseline_avg = (sum(baseline_values) / len(baseline_values)) if baseline_values else segment_avg

    relative = (segment_avg / baseline_avg) if baseline_avg > 0 else 1.0
    boost = max(MIN_BOOST, min(MAX_BOOST, relative))

    return HistoricalPerformance(
        sample_size=sample_size,
        segment_average_delivered_pct=segment_avg,
        baseline_average_delivered_pct=baseline_avg,
        boost=boost,
    )
