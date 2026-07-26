import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum, ForeignKey, Integer, String, Text
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
    # `location` holds the Rwandan District (unchanged column — matching.py compares on
    # it) — the four columns below add the rest of the administrative hierarchy sourced
    # from rwandasdata.csv, purely for display and the Google Maps embed. `admin_*` is
    # prefixed to avoid colliding with `sector` below, which means industry/niche here.
    province: Mapped[str | None] = mapped_column(String(64), default=None)
    location: Mapped[str | None] = mapped_column(String(128), default=None)
    admin_sector: Mapped[str | None] = mapped_column(String(128), default=None)
    admin_cell: Mapped[str | None] = mapped_column(String(128), default=None)
    admin_village: Mapped[str | None] = mapped_column(String(128), default=None)
    address_detail: Mapped[str | None] = mapped_column(String(255), default=None)
    sector: Mapped[str | None] = mapped_column(String(128), default=None)
    bio: Mapped[str | None] = mapped_column(Text, default=None)
    # Longer-form "my story" narrative — separate from `bio` (a short blurb) for
    # career highlights/journey, shown on the account settings / public profile page.
    legacy: Mapped[str | None] = mapped_column(Text, default=None)
    profile_picture_url: Mapped[str | None] = mapped_column(String(512), default=None)

    # See Brand.visibility_settings — same sparse "what I've turned off" convention.
    visibility_settings: Mapped[dict] = mapped_column(JSON, default=dict)

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
