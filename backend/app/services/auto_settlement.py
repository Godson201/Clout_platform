from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.platform_capabilities import get_capabilities
from app.core.security import as_aware_utc
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.campaign_slot import CampaignSlot
from app.models.enums import SlotStatus, SocialPostStatus
from app.models.influencer import Influencer
from app.models.post_metric_snapshot import PostMetricSnapshot
from app.models.social_post import SocialPost
from app.services.slot_recovery import settle_and_recover


async def find_slots_awaiting_settlement(db: AsyncSession) -> list[tuple[CampaignSlot, SocialPost]]:
    """Slots whose campaign's performance window has closed since the post went
    live (anchored to publish time, not claim time — a slot claimed early but
    posted late shouldn't have its window quietly run out before the ad was
    even up), still sitting in PUBLISHED/TRACKING. Returned regardless of
    whether they can actually be auto-settled — see auto_settle_expired_slots
    for that split.
    """
    stmt = (
        select(CampaignSlot, Campaign, SocialPost)
        .join(Campaign, CampaignSlot.campaign_id == Campaign.id)
        .join(SocialPost, SocialPost.campaign_slot_id == CampaignSlot.id)
        .where(
            CampaignSlot.status.in_([SlotStatus.PUBLISHED, SlotStatus.TRACKING]),
            SocialPost.status == SocialPostStatus.PUBLISHED,
            SocialPost.published_at.isnot(None),
        )
    )
    rows = (await db.execute(stmt)).all()

    now = datetime.now(timezone.utc)
    expired: list[tuple[CampaignSlot, SocialPost]] = []
    for slot, campaign, post in rows:
        deadline = as_aware_utc(post.published_at) + timedelta(days=campaign.performance_window_days)
        if deadline <= now:
            expired.append((slot, post))
    return expired


async def auto_settle_expired_slots(db: AsyncSession) -> dict[str, int]:
    """Runs on a schedule (see app/tasks/settlement_tasks.py). For every slot
    whose window has closed: if its platform's metrics are actually verifiable
    (see app.core.platform_capabilities — today that's mock mode only, no real
    platform has granted CLOUT that access yet), delivered_pct is computed from
    the post's latest metric snapshot and the slot is settled automatically,
    same as an admin would via the manual bridge. Everywhere else, the slot is
    left exactly where it is — untouched, not auto-failed — since CLOUT has no
    way to verify what actually happened; it just becomes findable via
    GET /admin/slots/awaiting-settlement for a human to check.
    """
    expired = await find_slots_awaiting_settlement(db)

    auto_settled = 0
    needs_review = 0

    for slot, post in expired:
        if not get_capabilities(slot.platform).can_fetch_metrics:
            needs_review += 1
            continue

        snapshot_result = await db.execute(
            select(PostMetricSnapshot)
            .where(PostMetricSnapshot.social_post_id == post.id)
            .order_by(PostMetricSnapshot.fetched_at.desc())
        )
        latest = snapshot_result.scalars().first()
        verified_views = latest.views if latest is not None else 0

        if slot.target_views > 0:
            delivered_pct = min(Decimal(100), (Decimal(verified_views) / Decimal(slot.target_views)) * Decimal(100))
        else:
            delivered_pct = Decimal(0)

        await settle_and_recover(db, slot=slot, delivered_pct=delivered_pct, actor_user_id=None)
        auto_settled += 1

    return {"auto_settled": auto_settled, "needs_review": needs_review}


async def get_awaiting_settlement_queue(
    db: AsyncSession,
) -> list[tuple[CampaignSlot, Campaign, SocialPost, Brand, Influencer, datetime]]:
    """The admin worklist: expired slots that genuinely need a human, because
    their platform's metrics aren't verifiable (today: every real platform).
    Auto-settleable expired slots aren't included — the scheduled task clears
    those on its own, no admin action is ever needed for them.
    """
    expired = await find_slots_awaiting_settlement(db)

    queue: list[tuple[CampaignSlot, Campaign, SocialPost, Brand, Influencer, datetime]] = []
    for slot, post in expired:
        if get_capabilities(slot.platform).can_fetch_metrics:
            continue  # handled automatically, not a review item

        campaign_result = await db.execute(select(Campaign).where(Campaign.id == slot.campaign_id))
        campaign = campaign_result.scalar_one()
        brand_result = await db.execute(select(Brand).where(Brand.id == campaign.brand_id))
        brand = brand_result.scalar_one()
        influencer_result = await db.execute(select(Influencer).where(Influencer.id == slot.influencer_id))
        influencer = influencer_result.scalar_one()

        window_closed_at = as_aware_utc(post.published_at) + timedelta(days=campaign.performance_window_days)
        queue.append((slot, campaign, post, brand, influencer, window_closed_at))

    queue.sort(key=lambda row: row[5])  # oldest-overdue first
    return queue
