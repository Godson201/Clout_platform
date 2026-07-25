import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import AdvertisementStatus
from app.models.mixins import TimestampMixin, UUIDPk

if TYPE_CHECKING:
    from app.models.advertisement_asset import AdvertisementAsset


class Advertisement(UUIDPk, TimestampMixin, Base):
    """A brand's in-progress or finished short-form ad, built from a template.
    Campaign linkage (which platforms it was actually distributed on, by whom)
    is Phase 3 — this table only owns creative content and its uploaded assets.
    """

    __tablename__ = "advertisements"

    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("advertisement_templates.id"))

    title: Mapped[str] = mapped_column(String(255))
    status: Mapped[AdvertisementStatus] = mapped_column(
        Enum(AdvertisementStatus, name="advertisement_status", values_callable=lambda e: [m.value for m in e]),
        default=AdvertisementStatus.DRAFT,
    )

    script_text: Mapped[str | None] = mapped_column(Text, default=None)
    cta_text: Mapped[str | None] = mapped_column(String(255), default=None)
    hashtags: Mapped[list[str]] = mapped_column(JSON, default=list)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, default=None)

    assets: Mapped[list["AdvertisementAsset"]] = relationship(
        back_populates="advertisement", cascade="all, delete-orphan"
    )
