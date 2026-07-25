import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import PaymentProvider, PaymentStatus
from app.models.mixins import TimestampMixin, UUIDPk


class Refund(UUIDPk, TimestampMixin, Base):
    """A disbursement back to the brand's MoMo number, issued when a funded
    campaign is cancelled before any slot is claimed (see services/refunds.py).
    Mirrors Payout's shape since both are "disburse money out of an internal
    wallet to an external MoMo number" operations.
    """

    __tablename__ = "refunds"

    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)

    provider: Mapped[PaymentProvider] = mapped_column(
        Enum(PaymentProvider, name="payment_provider", values_callable=lambda e: [m.value for m in e])
    )
    provider_reference: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    phone_number: Mapped[str] = mapped_column(String(32))
    amount: Mapped[float] = mapped_column(Numeric(20, 4))
    currency: Mapped[str] = mapped_column(String(3))

    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, name="payment_status", values_callable=lambda e: [m.value for m in e]),
        default=PaymentStatus.PENDING,
    )
    raw_provider_payload: Mapped[dict | None] = mapped_column(JSON, default=None)
    failure_reason: Mapped[str | None] = mapped_column(Text, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
