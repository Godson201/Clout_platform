import uuid

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPk


class AssetComment(UUIDPk, TimestampMixin, Base):
    """Internal feedback thread on a draft ad asset — for the brand and admin
    to discuss a specific upload during review, richer than the single
    rejection-reason field on AssetModerationStatus.REJECTED. Never shown to
    influencers; assets aren't broadcast-visible until approved anyway.
    """

    __tablename__ = "asset_comments"

    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("advertisement_assets.id", ondelete="CASCADE"), index=True)
    author_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    body: Mapped[str] = mapped_column(Text)
