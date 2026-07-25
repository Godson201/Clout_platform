from sqlalchemy import Enum, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import SocialPlatform
from app.models.mixins import TimestampMixin, UUIDPk


class ViewRate(UUIDPk, TimestampMixin, Base):
    """Admin-configurable RWF-per-view rate, one row per platform. Campaigns snapshot
    the rate at creation time (see Campaign.rate_snapshot), so updating a row here
    never retroactively changes an already-priced campaign — no versioning table
    needed, `audit_logs` already captures the change history.
    """

    __tablename__ = "view_rates"

    platform: Mapped[SocialPlatform] = mapped_column(
        Enum(SocialPlatform, name="social_platform", values_callable=lambda e: [m.value for m in e]), unique=True
    )
    rate_per_view: Mapped[float] = mapped_column(Numeric(10, 4))
    currency: Mapped[str] = mapped_column(String(3), default="RWF")
