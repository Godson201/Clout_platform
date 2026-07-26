import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import ContractStatus
from app.models.mixins import TimestampMixin, UUIDPk


class Contract(UUIDPk, TimestampMixin, Base):
    """A lightweight digital agreement between a brand and an influencer —
    freeform terms text proposed by one party, accepted/declined by the other.
    Not a legally-binding e-signature product; just a timestamped mutual
    acknowledgement record, gated on the same relationship check as messaging.
    """

    __tablename__ = "contracts"

    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), index=True)
    influencer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("influencers.id", ondelete="CASCADE"), index=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("campaigns.id", ondelete="SET NULL"), default=None)

    title: Mapped[str] = mapped_column(String(255))
    terms_text: Mapped[str] = mapped_column(Text)

    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus, name="contract_status", values_callable=lambda e: [m.value for m in e]),
        default=ContractStatus.PROPOSED,
    )
    proposed_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    responded_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
