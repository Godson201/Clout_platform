import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import CampaignStatus, FollowerTier
from app.models.mixins import TimestampMixin, UUIDPk

if TYPE_CHECKING:
    from app.models.campaign_slot import CampaignSlot


class Campaign(UUIDPk, TimestampMixin, Base):
    """A brand's funded (eventually) request to distribute one Advertisement
    through matched influencers. `target_views` is interpreted per selected
    platform — a campaign targeting [tiktok, instagram] at 100,000 views wants
    100k on *each*, not 100k split between them, matching the pricing example
    in the product spec directly when there's a single platform.
    """

    __tablename__ = "campaigns"

    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), index=True)
    advertisement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("advertisements.id"))

    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, name="campaign_status", values_callable=lambda e: [m.value for m in e]),
        default=CampaignStatus.DRAFT,
    )

    platforms: Mapped[list[str]] = mapped_column(JSON)
    target_views: Mapped[int] = mapped_column(Integer)
    tier: Mapped[FollowerTier] = mapped_column(
        Enum(FollowerTier, name="follower_tier", values_callable=lambda e: [m.value for m in e])
    )
    slot_count: Mapped[int] = mapped_column(Integer)
    performance_window_days: Mapped[int] = mapped_column(Integer, default=3)

    target_sector: Mapped[str | None] = mapped_column(String(128), default=None)
    target_location: Mapped[str | None] = mapped_column(String(128), default=None)

    # Snapshots — never re-read from view_rates/fee_configs after creation, so an
    # admin rate/fee change never retroactively alters an already-priced campaign.
    rate_snapshot: Mapped[dict[str, str]] = mapped_column(JSON)
    brand_fee_pct: Mapped[float] = mapped_column(Numeric(5, 4))
    base_price: Mapped[float] = mapped_column(Numeric(20, 4))
    total_brand_payment: Mapped[float] = mapped_column(Numeric(20, 4))
    currency: Mapped[str] = mapped_column(String(3), default="RWF")

    slots: Mapped[list["CampaignSlot"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
