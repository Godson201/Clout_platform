from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_token
from app.core.platform_capabilities import get_capabilities
from app.models.campaign_slot import CampaignSlot
from app.models.enums import SlotStatus, SocialPostStatus
from app.models.post_metric_snapshot import PostMetricSnapshot
from app.models.social_account import SocialAccount
from app.models.social_post import SocialPost
from app.services.social import get_adapter


async def poll_post_metrics(db: AsyncSession, *, post: SocialPost) -> PostMetricSnapshot | None:
    """Returns None (a no-op, not an error) whenever metrics genuinely can't be
    fetched right now — the platform doesn't support it yet, or this is a
    manually-submitted post with no platform-native id to query. Every actual
    fetch is appended as a new snapshot, never overwriting the last one, so
    growth (and deletion — Scenario E from the payment-integrity analysis) is
    visible across the whole series, not just the latest reading.
    """
    if post.status != SocialPostStatus.PUBLISHED or post.external_post_id is None:
        return None

    if not get_capabilities(post.platform).can_fetch_metrics:
        return None

    if post.social_account_id is None:
        return None
    account_result = await db.execute(select(SocialAccount).where(SocialAccount.id == post.social_account_id))
    account = account_result.scalar_one_or_none()
    if account is None:
        return None

    adapter = get_adapter(post.platform)
    access_token = decrypt_token(account.access_token_encrypted)
    metrics = await adapter.fetch_metrics(access_token=access_token, external_post_id=post.external_post_id)

    slot_result = await db.execute(select(CampaignSlot).where(CampaignSlot.id == post.campaign_slot_id))
    slot = slot_result.scalar_one_or_none()

    if not metrics.post_exists:
        post.status = SocialPostStatus.DELETED
        if slot is not None and slot.status in (SlotStatus.PUBLISHED, SlotStatus.TRACKING):
            slot.status = SlotStatus.FAILED
        await db.commit()
        return None

    snapshot = PostMetricSnapshot(
        social_post_id=post.id,
        views=metrics.views,
        likes=metrics.likes,
        comments=metrics.comments,
        shares=metrics.shares,
        # Explicit Python-side timestamp rather than relying on the column's
        # server_default: SQLite's CURRENT_TIMESTAMP only has second resolution,
        # so two snapshots for the same post recorded within the same second
        # would tie and make "the latest snapshot" (ORDER BY fetched_at DESC)
        # ambiguous — a real correctness bug, not just a test artifact, since
        # frequent polling of an active post is exactly the normal case.
        fetched_at=datetime.now(timezone.utc),
    )
    db.add(snapshot)

    if slot is not None and slot.status == SlotStatus.PUBLISHED:
        slot.status = SlotStatus.TRACKING

    await db.commit()
    await db.refresh(snapshot)
    return snapshot
