import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campaign_slot import CampaignSlot
from app.models.comment import Comment
from app.models.comment_analysis import CommentAnalysis
from app.models.social_post import SocialPost


@dataclass(frozen=True)
class CommentSentimentSummary:
    total_comments: int
    category_counts: dict[str, int]
    average_sentiment_score: float | None
    sample_questions: list[str]


async def compute_comment_summary(db: AsyncSession, *, campaign_id: uuid.UUID) -> CommentSentimentSummary:
    """Every number here is a straight count/average over stored Comment +
    CommentAnalysis rows — same "nothing estimated" contract as
    compute_campaign_analytics, since this feeds the same AI report guardrail.
    """
    rows = (
        await db.execute(
            select(Comment, CommentAnalysis)
            .join(CommentAnalysis, CommentAnalysis.comment_id == Comment.id)
            .join(SocialPost, Comment.social_post_id == SocialPost.id)
            .join(CampaignSlot, SocialPost.campaign_slot_id == CampaignSlot.id)
            .where(CampaignSlot.campaign_id == campaign_id)
        )
    ).all()

    category_counts: dict[str, int] = {}
    sentiment_scores: list[float] = []
    sample_questions: list[str] = []

    for comment, analysis in rows:
        category_counts[analysis.category.value] = category_counts.get(analysis.category.value, 0) + 1
        sentiment_scores.append(analysis.sentiment_score)
        if analysis.category.value == "question" and len(sample_questions) < 5:
            sample_questions.append(comment.text)

    average_sentiment_score = round(sum(sentiment_scores) / len(sentiment_scores), 4) if sentiment_scores else None

    return CommentSentimentSummary(
        total_comments=len(rows),
        category_counts=category_counts,
        average_sentiment_score=average_sentiment_score,
        sample_questions=sample_questions,
    )
