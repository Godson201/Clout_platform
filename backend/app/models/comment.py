import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import UUIDPk

if TYPE_CHECKING:
    from app.models.comment_analysis import CommentAnalysis


class Comment(UUIDPk, Base):
    """One comment fetched from a published post. `external_comment_id` is
    unique per post (not globally) so the same platform-assigned id can't
    collide across different posts/platforms; polling is idempotent against
    this constraint — refetching a post's comments never creates duplicates.
    """

    __tablename__ = "comments"
    __table_args__ = (UniqueConstraint("social_post_id", "external_comment_id", name="uq_comment_post_external_id"),)

    social_post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("social_posts.id", ondelete="CASCADE"), index=True)
    external_comment_id: Mapped[str] = mapped_column(String(128))
    author_handle: Mapped[str] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    analysis: Mapped["CommentAnalysis | None"] = relationship(
        back_populates="comment", uselist=False, cascade="all, delete-orphan"
    )
