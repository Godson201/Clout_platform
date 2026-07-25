from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_token
from app.core.platform_capabilities import get_capabilities
from app.core.security import as_aware_utc
from app.models.comment import Comment
from app.models.comment_analysis import CommentAnalysis
from app.models.enums import SocialPostStatus
from app.models.social_account import SocialAccount
from app.models.social_post import SocialPost
from app.services.comment_analysis import get_classifier
from app.services.social import get_adapter


async def poll_post_comments(db: AsyncSession, *, post: SocialPost) -> list[Comment]:
    """Fetches only comments newer than the last one already stored for this
    post (adapters filter by `since`), then classifies and persists each new
    one. Idempotent against the (social_post_id, external_comment_id) unique
    constraint even if an adapter ever returns an already-seen comment.
    Returns [] (a no-op, not an error) whenever comments genuinely can't be
    fetched — the platform doesn't support it, or this post has no
    platform-native id (a manually-submitted post).
    """
    if post.status != SocialPostStatus.PUBLISHED or post.external_post_id is None:
        return []
    if not get_capabilities(post.platform).can_fetch_comments:
        return []
    if post.social_account_id is None:
        return []

    account_result = await db.execute(select(SocialAccount).where(SocialAccount.id == post.social_account_id))
    account = account_result.scalar_one_or_none()
    if account is None:
        return []

    latest_result = await db.execute(
        select(Comment).where(Comment.social_post_id == post.id).order_by(Comment.posted_at.desc())
    )
    latest_comment = latest_result.scalars().first()
    # SQLite (tests) drops tzinfo on round-trip even for DateTime(timezone=True)
    # columns; Postgres (production) preserves it — normalize so the adapter's
    # comparison against its own tz-aware timestamps is correct on both.
    since = as_aware_utc(latest_comment.posted_at) if latest_comment is not None and latest_comment.posted_at is not None else None

    adapter = get_adapter(post.platform)
    access_token = decrypt_token(account.access_token_encrypted)
    fetched = await adapter.fetch_comments(access_token=access_token, external_post_id=post.external_post_id, since=since)

    classifier = get_classifier()
    new_comments: list[Comment] = []

    for item in fetched:
        existing = await db.execute(
            select(Comment).where(
                Comment.social_post_id == post.id, Comment.external_comment_id == item.external_comment_id
            )
        )
        if existing.scalar_one_or_none() is not None:
            continue

        comment = Comment(
            social_post_id=post.id,
            external_comment_id=item.external_comment_id,
            author_handle=item.author_handle,
            text=item.text,
            posted_at=item.posted_at,
        )
        db.add(comment)
        await db.flush()  # populates comment.id for the CommentAnalysis FK below

        result = classifier.classify(item.text)
        db.add(
            CommentAnalysis(
                comment_id=comment.id,
                category=result.category,
                sentiment_label=result.sentiment_label,
                sentiment_score=result.sentiment_score,
                classifier_version=result.classifier_version,
            )
        )
        new_comments.append(comment)

    await db.commit()
    for comment in new_comments:
        await db.refresh(comment)
    return new_comments
