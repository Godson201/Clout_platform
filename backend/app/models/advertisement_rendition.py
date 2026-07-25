import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import RenditionStatus, SocialPlatform
from app.models.mixins import TimestampMixin, UUIDPk

if TYPE_CHECKING:
    from app.models.advertisement_asset import AdvertisementAsset


class AdvertisementRendition(UUIDPk, TimestampMixin, Base):
    """One platform-specific FFmpeg export (aspect ratio, resolution, max duration,
    bitrate per app.core.platform_specs) generated from a source video asset.
    """

    __tablename__ = "advertisement_renditions"
    __table_args__ = (UniqueConstraint("asset_id", "platform", name="uq_rendition_asset_platform"),)

    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("advertisement_assets.id", ondelete="CASCADE"), index=True)
    platform: Mapped[SocialPlatform] = mapped_column(
        Enum(SocialPlatform, name="social_platform", values_callable=lambda e: [m.value for m in e])
    )

    storage_key: Mapped[str | None] = mapped_column(String(512), default=None)
    width: Mapped[int | None] = mapped_column(Integer, default=None)
    height: Mapped[int | None] = mapped_column(Integer, default=None)
    duration_seconds: Mapped[float | None] = mapped_column(Float, default=None)

    status: Mapped[RenditionStatus] = mapped_column(
        Enum(RenditionStatus, name="rendition_status", values_callable=lambda e: [m.value for m in e]),
        default=RenditionStatus.PENDING,
    )
    error_message: Mapped[str | None] = mapped_column(Text, default=None)

    asset: Mapped["AdvertisementAsset"] = relationship(back_populates="renditions")
