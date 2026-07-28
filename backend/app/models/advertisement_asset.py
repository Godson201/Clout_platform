import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import AssetModerationStatus, AssetStatus, AssetType
from app.models.mixins import TimestampMixin, UUIDPk

if TYPE_CHECKING:
    from app.models.advertisement import Advertisement
    from app.models.advertisement_rendition import AdvertisementRendition


class AdvertisementAsset(UUIDPk, TimestampMixin, Base):
    """One uploaded file (video/image/logo/audio/voiceover) attached to an
    advertisement. `storage_key` is a server-generated UUID-based path, never the
    client's original filename, so a malicious filename can't be used for path
    traversal or to overwrite another asset's file.
    """

    __tablename__ = "advertisement_assets"

    advertisement_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("advertisements.id", ondelete="CASCADE"), index=True
    )

    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="asset_type", values_callable=lambda e: [m.value for m in e])
    )
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(128))
    file_size_bytes: Mapped[int] = mapped_column(Integer)

    duration_seconds: Mapped[float | None] = mapped_column(Float, default=None)
    width: Mapped[int | None] = mapped_column(Integer, default=None)
    height: Mapped[int | None] = mapped_column(Integer, default=None)

    status: Mapped[AssetStatus] = mapped_column(
        Enum(AssetStatus, name="asset_status", values_callable=lambda e: [m.value for m in e]),
        default=AssetStatus.UPLOADED,
    )
    error_message: Mapped[str | None] = mapped_column(Text, default=None)

    # Separate from `status` above: `status` tracks the FFmpeg processing
    # pipeline (is it playable yet?), this tracks admin review (has it been
    # cleared to broadcast to influencers?). See AssetModerationStatus docstring.
    moderation_status: Mapped[AssetModerationStatus] = mapped_column(
        Enum(AssetModerationStatus, name="asset_moderation_status", values_callable=lambda e: [m.value for m in e]),
        default=AssetModerationStatus.PENDING,
    )
    moderation_note: Mapped[str | None] = mapped_column(Text, default=None)
    moderated_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    advertisement: Mapped["Advertisement"] = relationship(back_populates="assets")
    renditions: Mapped[list["AdvertisementRendition"]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
