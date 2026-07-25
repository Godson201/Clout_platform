import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign_slot import CampaignSlot
from app.models.enums import FollowerTier, SocialAccountStatus, SocialPlatform, SocialPostStatus
from app.models.influencer import Influencer
from app.models.post_metric_snapshot import PostMetricSnapshot
from app.models.social_account import SocialAccount
from app.models.social_post import SocialPost

# Weighted-scoring v1: explainable and rule-based rather than ML, since there's
# still no meaningful volume of historical campaign-OUTCOME data to train a
# ranking model against. Phase 8 adds a separate, optional historical-
# performance multiplier on top of this (see services/recommendations.py)
# rather than folding statistics into these hand-set weights, so the
# explainable breakdown below always stays legible on its own.
WEIGHTS = {
    "sector": 0.20,
    "location": 0.10,
    "tier": 0.20,
    "reliability": 0.20,
    "platform": 0.15,
    "engagement": 0.15,
}

_TIER_ORDER = [FollowerTier.NANO, FollowerTier.MICRO, FollowerTier.MID, FollowerTier.MACRO]

# A short-form video engagement rate ((likes+comments+shares)/views) at or
# above this is treated as a full-marks score — roughly what's considered
# strong engagement for the format; not platform-specific since all four
# adapters report engagement in this shape.
STRONG_ENGAGEMENT_RATE = 0.10

# Neutral reliability for an influencer with no settled slots yet — not
# penalized as unreliable, but not assumed excellent either.
NEUTRAL_RELIABILITY = 0.6


@dataclass(frozen=True)
class MatchScoreBreakdown:
    sector_score: float
    location_score: float
    tier_score: float
    reliability_score: float
    platform_score: float
    engagement_score: float
    total: float


def _tier_fit(requested: FollowerTier, actual: FollowerTier | None) -> float:
    if actual is None:
        return 0.4  # unset tier: still eligible, scored conservatively rather than excluded
    if actual == requested:
        return 1.0
    distance = abs(_TIER_ORDER.index(actual) - _TIER_ORDER.index(requested))
    return max(0.0, 1.0 - distance * 0.35)


def _text_match(requested: str | None, actual: str | None) -> float:
    if requested is None:
        return 0.5  # brand didn't target this dimension — neutral, not a mismatch
    if actual is None:
        return 0.0
    return 1.0 if requested.strip().lower() == actual.strip().lower() else 0.0


def _platform_fit(slot_platform: SocialPlatform, active_platforms: set[SocialPlatform]) -> float:
    # Not connected isn't disqualifying — connecting an account takes one
    # click and shouldn't hide a genuinely well-matched influencer who just
    # hasn't bothered to link this platform yet.
    return 1.0 if slot_platform in active_platforms else 0.3


def _engagement_fit(engagement_rate: float | None) -> float:
    if engagement_rate is None:
        return 0.5  # neutral default — no published posts with metrics yet
    return min(1.0, engagement_rate / STRONG_ENGAGEMENT_RATE)


def score_slot_for_influencer(
    slot: CampaignSlot,
    *,
    campaign_sector: str | None,
    campaign_location: str | None,
    influencer: Influencer,
    active_platforms: set[SocialPlatform],
    engagement_rate: float | None,
    reliability_score: float,
) -> MatchScoreBreakdown:
    sector_score = _text_match(campaign_sector, influencer.sector)
    location_score = _text_match(campaign_location, influencer.location)
    tier_score = _tier_fit(slot.tier, influencer.follower_tier)
    platform_score = _platform_fit(slot.platform, active_platforms)
    engagement_score = _engagement_fit(engagement_rate)

    total = (
        sector_score * WEIGHTS["sector"]
        + location_score * WEIGHTS["location"]
        + tier_score * WEIGHTS["tier"]
        + reliability_score * WEIGHTS["reliability"]
        + platform_score * WEIGHTS["platform"]
        + engagement_score * WEIGHTS["engagement"]
    )

    return MatchScoreBreakdown(
        sector_score=sector_score,
        location_score=location_score,
        tier_score=tier_score,
        reliability_score=reliability_score,
        platform_score=platform_score,
        engagement_score=engagement_score,
        total=round(total, 4),
    )


async def get_active_platforms(db: AsyncSession, influencer_id: uuid.UUID) -> set[SocialPlatform]:
    result = await db.execute(
        select(SocialAccount.platform).where(
            SocialAccount.owner_user_id == influencer_id, SocialAccount.status == SocialAccountStatus.ACTIVE
        )
    )
    return set(result.scalars().all())


async def get_reliability_score(db: AsyncSession, influencer_id: uuid.UUID) -> float:
    """Average delivered_pct/100 across every slot this influencer has actually
    had settled (COMPLETED, PARTIALLY_COMPLETED, or FAILED all set
    delivered_pct — see services/settlement.py). A slot delivered at 90% counts
    as 0.9, not lumped in with an outright failure the way the old binary
    completed/failed counter pair would — someone who consistently
    almost-delivers should out-rank someone who fails outright, which a
    complete/fail ratio alone can't distinguish.
    """
    result = await db.execute(
        select(CampaignSlot.delivered_pct).where(
            CampaignSlot.influencer_id == influencer_id, CampaignSlot.delivered_pct.isnot(None)
        )
    )
    values = [float(v) for v in result.scalars().all()]
    if not values:
        return NEUTRAL_RELIABILITY
    return (sum(values) / len(values)) / 100


async def get_engagement_rate(db: AsyncSession, influencer_id: uuid.UUID) -> float | None:
    """Average (likes+comments+shares)/views across the influencer's published
    posts, using each post's latest metric snapshot. None (not 0) when there's
    no metrics history yet, so `_engagement_fit` can tell "unproven" apart from
    "proven and poor" — the same neutral-default convention reliability uses.
    """
    posts_result = await db.execute(
        select(SocialPost.id)
        .join(CampaignSlot, SocialPost.campaign_slot_id == CampaignSlot.id)
        .where(CampaignSlot.influencer_id == influencer_id, SocialPost.status == SocialPostStatus.PUBLISHED)
    )
    post_ids = list(posts_result.scalars().all())
    if not post_ids:
        return None

    rates: list[float] = []
    for post_id in post_ids:
        snapshot_result = await db.execute(
            select(PostMetricSnapshot)
            .where(PostMetricSnapshot.social_post_id == post_id)
            .order_by(PostMetricSnapshot.fetched_at.desc())
        )
        latest = snapshot_result.scalars().first()
        if latest is None or latest.views <= 0:
            continue
        rates.append((latest.likes + latest.comments + (latest.shares or 0)) / latest.views)

    if not rates:
        return None
    return sum(rates) / len(rates)
