import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, String, Text
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
    location: Mapped[str | None] = mapped_column(String(128), default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    website: Mapped[str | None] = mapped_column(String(255), default=None)
    logo_url: Mapped[str | None] = mapped_column(String(512), default=None)
    contact_phone: Mapped[str | None] = mapped_column(String(32), default=None)
    contact_email: Mapped[str | None] = mapped_column(String(255), default=None)

    verification_status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status", values_callable=lambda e: [m.value for m in e]),
        default=VerificationStatus.UNVERIFIED,
    )

    user: Mapped["User"] = relationship(back_populates="brand")
