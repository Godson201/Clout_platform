import uuid

from pydantic import BaseModel


class InfluencerPerformanceRead(BaseModel):
    influencer_id: uuid.UUID
    username: str
    platform: str
    views: int
    likes: int
    comments: int
    shares: int


class CommentSentimentSummaryRead(BaseModel):
    total_comments: int
    category_counts: dict[str, int]
    average_sentiment_score: float | None
    sample_questions: list[str]


class CampaignAnalyticsRead(BaseModel):
    total_target_views: int
    total_verified_views: int
    progress_pct: float
    total_engagement: int
    views_by_platform: dict[str, int]
    engagement_by_platform: dict[str, int]
    influencer_performance: list[InfluencerPerformanceRead]
    top_influencer_username: str | None
    top_platform: str | None
    slot_status_counts: dict[str, int]
    comment_summary: CommentSentimentSummaryRead
