import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import PublishMode, SocialPlatform, SocialPostStatus
from app.models.mixins import TimestampMixin, UUIDPk


class SocialPost(UUIDPk, TimestampMixin, Base):
    """One per claimed CampaignSlot — the actual published (or pending) post
    that fulfills it. `publish_mode` is decided by the service layer from
    app.core.platform_capabilities at creation time, not chosen by the
    influencer: MANUAL means CLOUT generated the asset + instructions and is
    waiting on the influencer to submit the live post's URL; AUTO means the
    platform adapter published it directly (not reachable today — every
    platform's can_auto_publish is currently False).
    """

    __tablename__ = "social_posts"

    campaign_slot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign_slots.id", ondelete="CASCADE"), unique=True, index=True
    )
    social_account_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("social_accounts.id"), default=None)
    platform: Mapped[SocialPlatform] = mapped_column(
        Enum(SocialPlatform, name="social_platform", values_callable=lambda e: [m.value for m in e])
    )

    publish_mode: Mapped[PublishMode] = mapped_column(
        Enum(PublishMode, name="publish_mode", values_callable=lambda e: [m.value for m in e])
    )
    caption: Mapped[str] = mapped_column(Text)

    external_post_id: Mapped[str | None] = mapped_column(String(128), default=None)
    post_url: Mapped[str | None] = mapped_column(String(1024), default=None)

    status: Mapped[SocialPostStatus] = mapped_column(
        Enum(SocialPostStatus, name="social_post_status", values_callable=lambda e: [m.value for m in e]),
        default=SocialPostStatus.PENDING,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
