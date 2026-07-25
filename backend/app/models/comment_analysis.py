import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import CommentCategory, SentimentLabel
from app.models.mixins import UUIDPk

if TYPE_CHECKING:
    from app.models.comment import Comment


class CommentAnalysis(UUIDPk, Base):
    """1:1 with Comment. `classifier_version` records which classifier produced
    this row (see app/services/comment_analysis/) so re-running analysis after
    upgrading the classifier (rule-based v1 -> a real ML model later) is a
    visible, auditable change rather than a silent one.
    """

    __tablename__ = "comment_analyses"

    comment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), unique=True, index=True
    )
    category: Mapped[CommentCategory] = mapped_column(
        Enum(CommentCategory, name="comment_category", values_callable=lambda e: [m.value for m in e])
    )
    sentiment_label: Mapped[SentimentLabel] = mapped_column(
        Enum(SentimentLabel, name="sentiment_label", values_callable=lambda e: [m.value for m in e])
    )
    sentiment_score: Mapped[float] = mapped_column(Float)  # -1.0 (very negative) to 1.0 (very positive)
    classifier_version: Mapped[str] = mapped_column(String(64))
    analyzed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    comment: Mapped["Comment"] = relationship(back_populates="analysis")
