import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.mixins import UUIDPk

if TYPE_CHECKING:
    from app.models.brand import Brand
    from app.models.influencer import Influencer


class Conversation(UUIDPk, Base):
    """One thread between a specific brand and a specific influencer — found or
    created lazily on first message (see services/messaging.py), gated on them
    having an actual relationship (the influencer has claimed a slot on one of
    that brand's campaigns) so this can't become an open messaging directory.
    """

    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("brand_id", "influencer_id", name="uq_conversation_pair"),)

    brand_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), index=True)
    influencer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("influencers.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Denormalized for cheap inbox sorting — updated by services/messaging.py
    # every time a message lands, explicitly in Python rather than relying on a
    # DB trigger, matching how the rest of this codebase avoids DB-side logic.
    last_message_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    brand: Mapped["Brand"] = relationship()
    influencer: Mapped["Influencer"] = relationship()
