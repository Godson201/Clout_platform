import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import AnnouncementAudience
from app.models.mixins import TimestampMixin, UUIDPk


class Announcement(UUIDPk, TimestampMixin, Base):
    """Admin broadcast to brands, influencers, or both. `is_active` lets an
    admin retract one without deleting the record (audit trail)."""

    __tablename__ = "announcements"

    author_admin_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    audience: Mapped[AnnouncementAudience] = mapped_column(
        Enum(AnnouncementAudience, name="announcement_audience", values_callable=lambda e: [m.value for m in e])
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
