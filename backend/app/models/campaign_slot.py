import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import FollowerTier, SlotStatus, SocialPlatform
from app.models.mixins import TimestampMixin, UUIDPk

if TYPE_CHECKING:
    from app.models.campaign import Campaign
    from app.models.influencer import Influencer


# A slot's shortfall is recycled into at most this many successor slots before
# Phase 8's recovery engine gives up and refunds the remainder to the brand
# instead — without a cap, a chain of influencers each partially delivering
# could recycle the same shrinking remainder indefinitely.
MAX_RECOVERY_GENERATIONS = 2


class CampaignSlot(UUIDPk, TimestampMixin, Base):
    """One influencer-shaped allocation of a campaign's target views on one
    platform. Claiming a slot is the concurrency-critical operation in Phase 3
    — see services/slot_claim.py for the atomic conditional UPDATE that both
    prevents double-claims and enforces the 5-active-slots-per-influencer rule
    in a single statement (portable across SQLite and Postgres, unlike
    SELECT ... FOR UPDATE).

    `delivered_pct`/`recovered_from_slot_id`/`recovery_generation` are Phase 8
    additions: a slot's own status (COMPLETED/PARTIALLY_COMPLETED/FAILED)
    always records what *that influencer* actually delivered — it is never
    overwritten by what happens to the leftover budget afterward. Recovery is
    tracked separately via the self-referential chain so influencer reliability
    history (services/matching.py) stays accurate regardless of recycling.
    """

    __tablename__ = "campaign_slots"

    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    platform: Mapped[SocialPlatform] = mapped_column(
        Enum(SocialPlatform, name="social_platform", values_callable=lambda e: [m.value for m in e])
    )
    tier: Mapped[FollowerTier] = mapped_column(
        Enum(FollowerTier, name="follower_tier", values_callable=lambda e: [m.value for m in e])
    )
    target_views: Mapped[int] = mapped_column(Integer)
    budget_allocated: Mapped[float] = mapped_column(Numeric(20, 4))

    status: Mapped[SlotStatus] = mapped_column(
        Enum(SlotStatus, name="slot_status", values_callable=lambda e: [m.value for m in e]), default=SlotStatus.OPEN
    )
    influencer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("influencers.id"), default=None, index=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    # Set once, at settlement time — the fraction (0-100) of target_views this
    # specific slot's influencer was verified to have delivered.
    delivered_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), default=None)

    # Points at the *predecessor* slot this one recovers the shortfall of, if
    # any. A chain's length is recovery_generation (0 = an original slot never
    # recovered from anything).
    recovered_from_slot_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("campaign_slots.id", ondelete="SET NULL"), default=None
    )
    recovery_generation: Mapped[int] = mapped_column(Integer, default=0)

    campaign: Mapped["Campaign"] = relationship(back_populates="slots")
    influencer: Mapped["Influencer | None"] = relationship()
