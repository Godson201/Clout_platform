import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import FollowerTier, VerificationStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Influencer(TimestampMixin, Base):
    __tablename__ = "influencers"

    id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    display_name: Mapped[str] = mapped_column(String(255))
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    location: Mapped[str | None] = mapped_column(String(128), default=None)
    sector: Mapped[str | None] = mapped_column(String(128), default=None)
    bio: Mapped[str | None] = mapped_column(Text, default=None)

    # Self-reported until Phase 5 connects real social accounts (see FollowerTier).
    follower_tier: Mapped[FollowerTier | None] = mapped_column(
        Enum(FollowerTier, name="follower_tier", values_callable=lambda e: [m.value for m in e]), default=None
    )
    estimated_followers: Mapped[int | None] = mapped_column(Integer, default=None)

    # Updated as slots resolve (Phase 5+ tracking); read by the matching engine's
    # historical-completion-rate factor. Both start at 0, which the matching
    # service treats as "no history yet" rather than "100% failure".
    completed_slots_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_slots_count: Mapped[int] = mapped_column(Integer, default=0)

    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status", values_callable=lambda e: [m.value for m in e]),
        default=VerificationStatus.UNVERIFIED,
    )

    user: Mapped["User"] = relationship(back_populates="influencer")
