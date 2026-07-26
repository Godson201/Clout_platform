import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import MessageType
from app.models.mixins import UUIDPk


class Message(UUIDPk, Base):
    """A single chat message — text or a file attachment (audio/video/voice
    note/document). `created_at` is set explicitly in Python by
    services/messaging.py rather than via server_default=func.now(): SQLite's
    CURRENT_TIMESTAMP only has whole-second resolution, which makes ordering
    ambiguous for messages sent back-to-back (the same bug hit
    PostMetricSnapshot.fetched_at in Phase 6 — see app/services/social_metrics.py).
    """

    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    sender_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    message_type: Mapped[MessageType] = mapped_column(
        Enum(MessageType, name="message_type", values_callable=lambda e: [m.value for m in e])
    )
    text_body: Mapped[str | None] = mapped_column(Text, default=None)

    attachment_key: Mapped[str | None] = mapped_column(String(512), default=None)
    attachment_original_filename: Mapped[str | None] = mapped_column(String(255), default=None)
    attachment_mime_type: Mapped[str | None] = mapped_column(String(128), default=None)
    attachment_size_bytes: Mapped[int | None] = mapped_column(BigInteger, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
