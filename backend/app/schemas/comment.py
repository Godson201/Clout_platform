import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import CommentCategory, SentimentLabel


class CommentAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: CommentCategory
    sentiment_label: SentimentLabel
    sentiment_score: float
    classifier_version: str


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    author_handle: str
    text: str
    posted_at: datetime | None
    fetched_at: datetime
    analysis: CommentAnalysisRead | None
