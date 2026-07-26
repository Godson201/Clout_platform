import uuid
from datetime import date

from sqlalchemy import Date, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import HighlightCategory, ProfileOwnerType
from app.models.mixins import TimestampMixin, UUIDPk


class ProfileHighlight(UUIDPk, TimestampMixin, Base):
    """An award or an attended event on a brand's or influencer's profile.
    Polymorphic on (owner_type, owner_id) rather than two near-identical tables
    — same convention as Wallet's owner_type/owner_id — since awards and events
    share the same shape (title, optional subtitle/date/description).
    """

    __tablename__ = "profile_highlights"

    owner_type: Mapped[ProfileOwnerType] = mapped_column(
        Enum(ProfileOwnerType, name="profile_owner_type", values_callable=lambda e: [m.value for m in e]),
        index=True,
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(index=True)
    category: Mapped[HighlightCategory] = mapped_column(
        Enum(HighlightCategory, name="highlight_category", values_callable=lambda e: [m.value for m in e])
    )

    title: Mapped[str] = mapped_column(String(255))
    # Issuer for an award (e.g. "Rwanda Digital Awards"), venue/location for an
    # event (e.g. "Kigali Convention Centre") — same free-text slot either way.
    subtitle: Mapped[str | None] = mapped_column(String(255), default=None)
    occurred_on: Mapped[date | None] = mapped_column(Date, default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)
