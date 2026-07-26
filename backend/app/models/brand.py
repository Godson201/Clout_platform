import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import VerificationStatus
from app.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Brand(TimestampMixin, Base):
    __tablename__ = "brands"

    id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    business_name: Mapped[str] = mapped_column(String(255))
    sector: Mapped[str | None] = mapped_column(String(128), default=None)
    # `location` holds the Rwandan District (kept as its own column, unchanged, since
    # matching.py and campaign target_location filtering already compare on it) — the
    # four columns below add the rest of the real administrative hierarchy sourced from
    # rwandasdata.csv, purely for display and the Google Maps embed. `admin_*` is
    # prefixed to avoid colliding with `sector` above, which means industry/niche here.
    province: Mapped[str | None] = mapped_column(String(64), default=None)
    location: Mapped[str | None] = mapped_column(String(128), default=None)
    admin_sector: Mapped[str | None] = mapped_column(String(128), default=None)
    admin_cell: Mapped[str | None] = mapped_column(String(128), default=None)
    admin_village: Mapped[str | None] = mapped_column(String(128), default=None)
    address_detail: Mapped[str | None] = mapped_column(String(255), default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    # Free-text "our story" section — separate from `description` (a short
    # marketplace blurb) since this is meant for a longer narrative (history,
    # milestones) shown on the account settings / public profile page.
    legacy: Mapped[str | None] = mapped_column(Text, default=None)
    website: Mapped[str | None] = mapped_column(String(255), default=None)
    logo_url: Mapped[str | None] = mapped_column(String(512), default=None)
    contact_phone: Mapped[str | None] = mapped_column(String(32), default=None)
    contact_email: Mapped[str | None] = mapped_column(String(255), default=None)

    # Which profile sections are visible to other users on this account's public
    # profile (see app/schemas/public_profile.py). A key absent from the dict
    # means "visible" — this is a sparse "what I've turned off" set, not a
    # complete allow-list, so adding a new toggleable section never silently
    # hides it for existing accounts that predate that section.
    visibility_settings: Mapped[dict] = mapped_column(JSON, default=dict)

    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status", values_callable=lambda e: [m.value for m in e]),
        default=VerificationStatus.UNVERIFIED,
    )

    user: Mapped["User"] = relationship(back_populates="brand")
