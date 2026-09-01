"""Small, explainable recommendation layer for the native Clout feed.

It deliberately uses only first-party signals that Clout has actually observed:
follows, likes, saves, comments, shared hashtags, public engagement and
recency.  This avoids pretending a cold-start platform has a trained AI model
while still producing a useful, personalised feed.
"""
import math
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NativePostStatus, NativePostVisibility, UserType
from app.models.social_feed import Follow, Hashtag, NativePost, NativePostComment, NativePostHashtag, NativePostLike, NativePostSave, UserBlock
from app.models.user import User


async def _weighted_activity(
    db: AsyncSession, *, user_id: uuid.UUID, model, weight: float
) -> tuple[dict[uuid.UUID, float], dict[str, float]]:
    """Return creator and hashtag affinity from one engagement table."""
    creators: dict[uuid.UUID, float] = defaultdict(float)
    tags: dict[str, float] = defaultdict(float)
    rows = (
        await db.execute(
            select(NativePost.author_id, Hashtag.name)
            .select_from(model)
            .join(NativePost, NativePost.id == model.post_id)
            .outerjoin(NativePostHashtag, NativePostHashtag.post_id == NativePost.id)
            .outerjoin(Hashtag, Hashtag.id == NativePostHashtag.hashtag_id)
            .where(model.user_id == user_id if model is not NativePostComment else model.author_id == user_id)
        )
    ).all()
    for author_id, tag in rows:
        creators[author_id] += weight
        if tag:
            tags[tag] += weight
    return creators, tags


async def ranked_posts_for_user(db: AsyncSession, *, user: User, limit: int) -> list[NativePost]:
    """Rank a bounded candidate pool, then return the requested page size."""
    blocked = select(UserBlock.blocked_id).where(UserBlock.blocker_id == user.id)
    following = set((await db.execute(select(Follow.following_id).where(Follow.follower_id == user.id))).scalars().all())
    visibility = [NativePost.visibility == NativePostVisibility.PUBLIC, NativePost.author_id == user.id]
    if following:
        visibility.append(and_(NativePost.visibility == NativePostVisibility.FOLLOWERS, NativePost.author_id.in_(following)))
    if user.user_type == UserType.BRAND:
        visibility.append(NativePost.visibility == NativePostVisibility.BRANDS_ONLY)
    candidates = (
        await db.execute(
            select(NativePost)
            .where(NativePost.status == NativePostStatus.PUBLISHED, ~NativePost.author_id.in_(blocked), or_(*visibility))
            .order_by(NativePost.created_at.desc())
            .limit(250)
        )
    ).scalars().all()
    if not candidates:
        return []

    creator_scores: dict[uuid.UUID, float] = defaultdict(float)
    tag_scores: dict[str, float] = defaultdict(float)
    for model, weight in ((NativePostLike, 1.0), (NativePostSave, 2.5), (NativePostComment, 2.0)):
        creators, tags = await _weighted_activity(db, user_id=user.id, model=model, weight=weight)
        for key, value in creators.items():
            creator_scores[key] += value
        for key, value in tags.items():
            tag_scores[key] += value

    ids = [post.id for post in candidates]
    likes = dict((await db.execute(select(NativePostLike.post_id, func.count()).where(NativePostLike.post_id.in_(ids)).group_by(NativePostLike.post_id))).all())
    comments = dict((await db.execute(select(NativePostComment.post_id, func.count()).where(NativePostComment.post_id.in_(ids)).group_by(NativePostComment.post_id))).all())
    tag_rows = (await db.execute(select(NativePostHashtag.post_id, Hashtag.name).join(Hashtag).where(NativePostHashtag.post_id.in_(ids)))).all()
    post_tags: dict[uuid.UUID, list[str]] = defaultdict(list)
    for post_id, tag in tag_rows:
        post_tags[post_id].append(tag)

    now = datetime.now(timezone.utc)
    scored: list[tuple[float, NativePost]] = []
    for post in candidates:
        created = post.created_at if post.created_at.tzinfo else post.created_at.replace(tzinfo=timezone.utc)
        age_hours = max(0.0, (now - created).total_seconds() / 3600)
        affinity = creator_scores[post.author_id]
        hashtag_affinity = sum(tag_scores[tag] for tag in post_tags[post.id])
        following_boost = 5.0 if post.author_id in following else 0.0
        engagement = math.log1p(int(likes.get(post.id, 0)) + 2 * int(comments.get(post.id, 0)))
        recency = 3.0 * math.exp(-age_hours / 72)
        own_post_penalty = -2.0 if post.author_id == user.id else 0.0
        scored.append((affinity + hashtag_affinity + following_boost + engagement + recency + own_post_penalty, post))
    scored.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
    return [post for _, post in scored[:limit]]
