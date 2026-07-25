import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import PaymentProvider, PaymentStatus
from app.models.mixins import TimestampMixin, UUIDPk


class Payment(UUIDPk, TimestampMixin, Base):
    """A MoMo "request to pay" (collection) initiated to fund one campaign.
    `provider_reference` is the client-generated reference (MoMo's X-Reference-Id)
    used both as the idempotency key for this request and to poll/receive
    webhook status updates. Confirming a Payment (see services/campaign_funding.py)
    is what triggers the internal ledger Transaction — this row tracks the
    external provider's state machine, not money movement itself.
    """

    __tablename__ = "payments"

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
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
