import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import UUIDPk


class PostMetricSnapshot(UUIDPk, Base):
    """Append-only time-series row — every poll writes a new snapshot rather
    than overwriting the last one, so growth over time (and anomalies) can
    actually be analyzed later instead of only ever seeing the latest reading.
    """

    __tablename__ = "post_metric_snapshots"

    social_post_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("social_posts.id", ondelete="CASCADE"), index=True)

    views: Mapped[int] = mapped_column(Integer)
    likes: Mapped[int] = mapped_column(Integer)
    comments: Mapped[int] = mapped_column(Integer)
    shares: Mapped[int | None] = mapped_column(Integer, default=None)

    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
