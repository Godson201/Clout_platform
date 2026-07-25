import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import TransactionType
from app.models.mixins import UUIDPk


class Transaction(UUIDPk, Base):
    """Append-only double-entry ledger row. Never updated or deleted after creation —
    corrections happen via new offsetting transactions, never in-place edits, so the
    ledger stays a complete audit trail. Business logic that writes these rows arrives
    in later phases (escrow/payments); this table exists now so the schema never has
    to be retrofitted under live money movement.
    """

    __tablename__ = "transactions"

    debit_wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"), index=True)
    credit_wallet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("wallets.id"), index=True)

    amount: Mapped[float] = mapped_column(Numeric(20, 4))
    currency: Mapped[str] = mapped_column(String(3))

    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, name="transaction_type", values_callable=lambda e: [m.value for m in e])
    )

    # Idempotency key / external provider reference (e.g. MoMo transaction id).
    reference: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
