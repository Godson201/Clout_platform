import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import as_aware_utc
from app.models.advertisement import Advertisement
from app.models.campaign import Campaign
from app.models.campaign_slot import CampaignSlot
from app.models.enums import PaymentStatus
from app.models.influencer import Influencer
from app.models.payment import Payment
from app.models.post_metric_snapshot import PostMetricSnapshot
from app.models.social_post import SocialPost

VIEWS_OVER_TIME_WINDOW_DAYS = 30


@dataclass(frozen=True)
class DailyViews:
    day: date
    views: int


@dataclass(frozen=True)
class TopCampaign:
    campaign_id: uuid.UUID
    title: str
    platforms: list[str]
    influencer_avatars: list[str | None]
    total_views: int
    progress_pct: float
    status: str


@dataclass(frozen=True)
class BrandDashboardSummary:
    total_campaigns: int
    total_campaigns_mom_pct: float | None
    total_views: int
    total_views_mom_pct: float | None
    total_engagement: int
    total_engagement_mom_pct: float | None
    total_spent: float
    total_spent_mom_pct: float | None
    currency: str
    views_over_time: list[DailyViews]
    views_by_platform: dict[str, int]
    top_campaigns: list[TopCampaign]


def _month_bounds(now: datetime) -> tuple[datetime, datetime]:
    this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
    return this_month_start, last_month_start


def _mom_pct(this_period: float, last_period: float) -> float | None:
    if last_period <= 0:
        return None
    return round((this_period - last_period) / last_period * 100, 1)


def _latest_before(snapshots: list[PostMetricSnapshot], before: datetime | None) -> PostMetricSnapshot | None:
    """`snapshots` must already be sorted newest-first. Every comparison is
    done in Python via as_aware_utc (not a SQL WHERE clause) since SQLite —
    used in tests — drops tzinfo on DateTime(timezone=True) columns on
    round-trip while Postgres preserves it; comparing in the DB layer would
    silently misbehave on one of the two backends.
    """
    if before is None:
        return snapshots[0] if snapshots else None
    before_aware = as_aware_utc(before)
    for snap in snapshots:
        if as_aware_utc(snap.fetched_at) < before_aware:
            return snap
    return None


async def _snapshots_for_post(db: AsyncSession, post_id: uuid.UUID) -> list[PostMetricSnapshot]:
    result = await db.execute(
        select(PostMetricSnapshot)
        .where(PostMetricSnapshot.social_post_id == post_id)
        .order_by(PostMetricSnapshot.fetched_at.desc())
    )
    return list(result.scalars().all())


def _daily_view_series(snapshots_by_post: dict[uuid.UUID, list[PostMetricSnapshot]], *, since: datetime, now: datetime) -> list[DailyViews]:
    """Buckets each post's view-count *gain* (not the raw cumulative reading)
    by the day it was observed, then sums across posts — a poll only reports
    the platform's running total, so a day's contribution is the delta from
    that post's previous poll, never the absolute number."""
    since_aware = as_aware_utc(since)
    daily: dict[date, int] = defaultdict(int)

    for snapshots in snapshots_by_post.values():
        chronological = list(reversed(snapshots))  # snapshots are stored newest-first
        prev_views: int | None = None
        for snap in chronological:
            fetched_at = as_aware_utc(snap.fetched_at)
            if prev_views is not None and fetched_at >= since_aware:
                daily[fetched_at.date()] += max(snap.views - prev_views, 0)
            prev_views = snap.views

    days = [since.date() + timedelta(days=i) for i in range((now.date() - since.date()).days + 1)]
    return [DailyViews(day=d, views=daily.get(d, 0)) for d in days]


async def compute_brand_dashboard_summary(db: AsyncSession, *, brand_id: uuid.UUID) -> BrandDashboardSummary:
    now = datetime.now(timezone.utc)
    this_month_start, last_month_start = _month_bounds(now)

    campaigns = (await db.execute(select(Campaign).where(Campaign.brand_id == brand_id))).scalars().all()
    total_campaigns = len(campaigns)
    campaigns_this_month = sum(1 for c in campaigns if as_aware_utc(c.created_at) >= this_month_start)
    campaigns_last_month = sum(
        1 for c in campaigns if last_month_start <= as_aware_utc(c.created_at) < this_month_start
    )
    currency = campaigns[0].currency if campaigns else "RWF"
    campaign_by_id = {c.id: c for c in campaigns}

    advertisement_ids = {c.advertisement_id for c in campaigns}
    advertisement_titles: dict[uuid.UUID, str] = {}
    if advertisement_ids:
        ads = (await db.execute(select(Advertisement).where(Advertisement.id.in_(advertisement_ids)))).scalars().all()
        advertisement_titles = {ad.id: ad.title for ad in ads}

    payments = (
        (
            await db.execute(
                select(Payment)
                .join(Campaign, Campaign.id == Payment.campaign_id)
                .where(Campaign.brand_id == brand_id, Payment.status == PaymentStatus.SUCCESSFUL)
            )
        )
        .scalars()
        .all()
    )
    total_spent = float(sum(float(p.amount) for p in payments))
    spent_this_month = sum(
        float(p.amount) for p in payments if p.confirmed_at and as_aware_utc(p.confirmed_at) >= this_month_start
    )
    spent_last_month = sum(
        float(p.amount)
        for p in payments
        if p.confirmed_at and last_month_start <= as_aware_utc(p.confirmed_at) < this_month_start
    )

    slots = (
        (
            await db.execute(
                select(CampaignSlot).join(Campaign, Campaign.id == CampaignSlot.campaign_id).where(Campaign.brand_id == brand_id)
            )
        )
        .scalars()
        .all()
    )

    total_views = 0
    total_engagement = 0
    views_by_platform: dict[str, int] = defaultdict(int)
    views_this_month = 0.0
    views_last_month = 0.0
    engagement_this_month = 0.0
    engagement_last_month = 0.0
    per_campaign_views: dict[uuid.UUID, int] = defaultdict(int)
    per_campaign_avatars: dict[uuid.UUID, list[str | None]] = defaultdict(list)
    snapshots_by_post: dict[uuid.UUID, list[PostMetricSnapshot]] = {}

    for slot in slots:
        post_result = await db.execute(select(SocialPost).where(SocialPost.campaign_slot_id == slot.id))
        post = post_result.scalar_one_or_none()
        if post is None:
            continue

        snapshots = await _snapshots_for_post(db, post.id)
        latest = _latest_before(snapshots, before=None)
        if latest is None:
            continue
        snapshots_by_post[post.id] = snapshots

        engagement = latest.likes + latest.comments + (latest.shares or 0)
        total_views += latest.views
        total_engagement += engagement
        views_by_platform[slot.platform.value] += latest.views
        per_campaign_views[slot.campaign_id] += latest.views

        if slot.influencer_id is not None:
            influencer = (
                await db.execute(select(Influencer).where(Influencer.id == slot.influencer_id))
            ).scalar_one_or_none()
            per_campaign_avatars[slot.campaign_id].append(influencer.profile_picture_url if influencer else None)

        at_month_start = _latest_before(snapshots, before=this_month_start)
        at_last_month_start = _latest_before(snapshots, before=last_month_start)
        baseline_this = at_month_start.views if at_month_start else 0
        baseline_last = at_last_month_start.views if at_last_month_start else 0
        views_this_month += max(latest.views - baseline_this, 0)
        views_last_month += max(baseline_this - baseline_last, 0)

        engagement_at_month_start = (
            (at_month_start.likes + at_month_start.comments + (at_month_start.shares or 0)) if at_month_start else 0
        )
        engagement_at_last_month_start = (
            (at_last_month_start.likes + at_last_month_start.comments + (at_last_month_start.shares or 0))
            if at_last_month_start
            else 0
        )
        engagement_this_month += max(engagement - engagement_at_month_start, 0)
        engagement_last_month += max(engagement_at_month_start - engagement_at_last_month_start, 0)

    top_campaigns: list[TopCampaign] = []
    for campaign_id, views in sorted(per_campaign_views.items(), key=lambda kv: kv[1], reverse=True)[:5]:
        campaign = campaign_by_id.get(campaign_id)
        if campaign is None:
            continue
        target = sum(s.target_views for s in slots if s.campaign_id == campaign_id)
        progress_pct = round((views / target) * 100, 1) if target > 0 else 0.0
        top_campaigns.append(
            TopCampaign(
                campaign_id=campaign_id,
                title=advertisement_titles.get(campaign.advertisement_id, "Untitled campaign"),
                platforms=list(campaign.platforms),
                influencer_avatars=per_campaign_avatars.get(campaign_id, []),
                total_views=views,
                progress_pct=progress_pct,
                status=campaign.status.value,
            )
        )

    since = now - timedelta(days=VIEWS_OVER_TIME_WINDOW_DAYS)
    views_over_time = _daily_view_series(snapshots_by_post, since=since, now=now)

    return BrandDashboardSummary(
        total_campaigns=total_campaigns,
        total_campaigns_mom_pct=_mom_pct(campaigns_this_month, campaigns_last_month),
        total_views=total_views,
        total_views_mom_pct=_mom_pct(views_this_month, views_last_month),
        total_engagement=total_engagement,
        total_engagement_mom_pct=_mom_pct(engagement_this_month, engagement_last_month),
        total_spent=total_spent,
        total_spent_mom_pct=_mom_pct(spent_this_month, spent_last_month),
        currency=currency,
        views_over_time=views_over_time,
        views_by_platform=dict(views_by_platform),
        top_campaigns=top_campaigns,
    )
