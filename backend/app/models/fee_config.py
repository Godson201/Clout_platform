from sqlalchemy import Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPk


class FeeConfig(UUIDPk, TimestampMixin, Base):
    """Singleton row (services/fee_config.py enforces "exactly one") holding the
    platform's current take rates. Per the confirmed business decision, CLOUT
    charges both sides: `brand_fee_pct` is added on top of the brand's payment,
    `influencer_fee_pct` is deducted from influencer payouts (Phase 4). Campaigns
    snapshot brand_fee_pct at creation time so a later fee change never
    retroactively alters an already-priced campaign.
    """

    __tablename__ = "fee_configs"

    brand_fee_pct: Mapped[float] = mapped_column(Numeric(5, 4), default=0.10)
    influencer_fee_pct: Mapped[float] = mapped_column(Numeric(5, 4), default=0.10)
