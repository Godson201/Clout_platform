import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign_slot import CampaignSlot
from app.models.influencer import Influencer
from app.models.post_metric_snapshot import PostMetricSnapshot
from app.models.social_post import SocialPost


@dataclass(frozen=True)
class InfluencerPerformance:
    influencer_id: uuid.UUID
    username: str
    platform: str
    views: int
    likes: int
    comments: int
    shares: int


@dataclass(frozen=True)
class CampaignAnalytics:
    total_target_views: int
    total_verified_views: int
    progress_pct: float
    total_engagement: int
    views_by_platform: dict[str, int]
    engagement_by_platform: dict[str, int]
    influencer_performance: list[InfluencerPerformance]
    top_influencer_username: str | None
    top_platform: str | None
    slot_status_counts: dict[str, int]


async def compute_campaign_analytics(db: AsyncSession, *, campaign_id: uuid.UUID) -> CampaignAnalytics:
    """Every number here comes straight from CampaignSlot rows and each post's
    latest PostMetricSnapshot — nothing computed or estimated. This is
    deliberate: Phase 7's AI report generator will narrate these same figures,
    and it must never be in a position to invent a number this function
    didn't already produce from real data.
    """
    slots = (
        (await db.execute(select(CampaignSlot).where(CampaignSlot.campaign_id == campaign_id))).scalars().all()
    )

    total_target_views = sum(s.target_views for s in slots)
    slot_status_counts: dict[str, int] = {}
    for s in slots:
        slot_status_counts[s.status.value] = slot_status_counts.get(s.status.value, 0) + 1

    views_by_platform: dict[str, int] = {}
    engagement_by_platform: dict[str, int] = {}
    influencer_performance: list[InfluencerPerformance] = []
    total_verified_views = 0
    total_engagement = 0

    for slot in slots:
        post_result = await db.execute(select(SocialPost).where(SocialPost.campaign_slot_id == slot.id))
        post = post_result.scalar_one_or_none()
        if post is None:
            continue

        snapshot_result = await db.execute(
            select(PostMetricSnapshot)
            .where(PostMetricSnapshot.social_post_id == post.id)
            .order_by(PostMetricSnapshot.fetched_at.desc())
        )
        latest = snapshot_result.scalars().first()
        if latest is None:
            continue

        engagement = latest.likes + latest.comments + (latest.shares or 0)
        total_verified_views += latest.views
        total_engagement += engagement

        platform_key = slot.platform.value
        views_by_platform[platform_key] = views_by_platform.get(platform_key, 0) + latest.views
        engagement_by_platform[platform_key] = engagement_by_platform.get(platform_key, 0) + engagement

        if slot.influencer_id is not None:
            influencer_result = await db.execute(select(Influencer).where(Influencer.id == slot.influencer_id))
            influencer = influencer_result.scalar_one()
            influencer_performance.append(
                InfluencerPerformance(
                    influencer_id=influencer.id,
                    username=influencer.username,
                    platform=platform_key,
                    views=latest.views,
                    likes=latest.likes,
                    comments=latest.comments,
                    shares=latest.shares or 0,
                )
            )

    progress_pct = round((total_verified_views / total_target_views) * 100, 2) if total_target_views > 0 else 0.0
    top_influencer_username = (
        max(influencer_performance, key=lambda p: p.views).username if influencer_performance else None
    )
    top_platform = max(views_by_platform.items(), key=lambda kv: kv[1])[0] if views_by_platform else None

    return CampaignAnalytics(
        total_target_views=total_target_views,
        total_verified_views=total_verified_views,
        progress_pct=progress_pct,
        total_engagement=total_engagement,
        views_by_platform=views_by_platform,
        engagement_by_platform=engagement_by_platform,
        influencer_performance=influencer_performance,
        top_influencer_username=top_influencer_username,
        top_platform=top_platform,
        slot_status_counts=slot_status_counts,
    )
