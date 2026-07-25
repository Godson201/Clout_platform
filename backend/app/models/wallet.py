import uuid

from sqlalchemy import Enum, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import WalletOwnerType
from app.models.mixins import TimestampMixin, UUIDPk


class Wallet(UUIDPk, TimestampMixin, Base):
    """One wallet per brand, per influencer, and a single platform-revenue wallet.

    `balance` is a denormalized cache maintained transactionally alongside ledger
    writes in `Transaction` — the ledger remains the source of truth and is never
    overwritten; `balance` only exists so reads don't have to sum the ledger.
    """

    __tablename__ = "wallets"
    __table_args__ = (UniqueConstraint("owner_type", "owner_id", "currency", name="uq_wallet_owner_currency"),)

    owner_type: Mapped[WalletOwnerType] = mapped_column(
        Enum(WalletOwnerType, name="wallet_owner_type", values_callable=lambda e: [m.value for m in e])
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(default=None, index=True)

    currency: Mapped[str] = mapped_column(String(3), default="RWF")
    balance: Mapped[float] = mapped_column(Numeric(20, 4), default=0)
