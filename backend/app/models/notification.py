import uuid

from sqlalchemy import JSON, Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import NotificationType
from app.models.mixins import TimestampMixin, UUIDPk


class Notification(UUIDPk, TimestampMixin, Base):
    """A per-user in-app notification. Delivery is polling-based, same as
    messaging — the frontend refetches on an interval rather than a push
    channel. `data` carries type-specific structured payload (e.g. an
    advertisement id, or a publishing influencer's location) that the
    frontend can render without a follow-up request.
    """

    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, name="notification_type", values_callable=lambda e: [m.value for m in e])
    )
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    link: Mapped[str | None] = mapped_column(String(512), default=None)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
