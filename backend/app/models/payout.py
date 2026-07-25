import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import PaymentProvider, PaymentStatus
from app.models.mixins import TimestampMixin, UUIDPk


class Payout(UUIDPk, TimestampMixin, Base):
    """An influencer's withdrawal request. `amount` is the gross amount debited
    from the influencer's wallet at request time; `fee_amount` (using the
    influencer_fee_pct snapshotted at request time, not read live later) goes to
    the platform wallet immediately, and `net_amount` is what's actually sent to
    MoMo. If the disbursement ultimately fails, both ledger legs are reversed
    (see services/payouts.py) and `status` becomes FAILED.
    """

    __tablename__ = "payouts"

    influencer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("influencers.id", ondelete="CASCADE"), index=True)

    provider: Mapped[PaymentProvider] = mapped_column(
        Enum(PaymentProvider, name="payment_provider", values_callable=lambda e: [m.value for m in e])
    )
    provider_reference: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    phone_number: Mapped[str] = mapped_column(String(32))
    amount: Mapped[float] = mapped_column(Numeric(20, 4))
    fee_pct: Mapped[float] = mapped_column(Numeric(5, 4))
    fee_amount: Mapped[float] = mapped_column(Numeric(20, 4))
    net_amount: Mapped[float] = mapped_column(Numeric(20, 4))
    currency: Mapped[str] = mapped_column(String(3))

    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", values_callable=lambda e: [m.value for m in e]),
        default=PaymentStatus.PENDING,
    )
    raw_provider_payload: Mapped[dict | None] = mapped_column(JSON, default=None)
    failure_reason: Mapped[str | None] = mapped_column(Text, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
