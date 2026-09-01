import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPk

if TYPE_CHECKING:
    from app.models.campaign_slot import CampaignSlot
    from app.models.influencer import Influencer


class CampaignCreative(UUIDPk, TimestampMixin, Base):
    """The current in-progress native creative for a claimed campaign slot.

    A slot has one working creative. Uploading a replacement intentionally
    replaces this record so an influencer never accidentally publishes an old
    revision of an ad.
    """

    __tablename__ = "campaign_creatives"
    __table_args__ = (UniqueConstraint("campaign_slot_id", name="uq_campaign_creative_slot"),)

    campaign_slot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("campaign_slots.id", ondelete="CASCADE"), index=True
    )
    influencer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("influencers.id"), index=True)
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(128))
    duration_seconds: Mapped[float] = mapped_column(Float)
    native_post_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("native_posts.id", ondelete="SET NULL"), unique=True, default=None
    )

    slot: Mapped["CampaignSlot"] = relationship()
    influencer: Mapped["Influencer"] = relationship()
