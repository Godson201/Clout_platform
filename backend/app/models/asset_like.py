import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.mixins import TimestampMixin, UUIDPk


class AssetLike(UUIDPk, TimestampMixin, Base):
    """A quick approve/like reaction on a draft ad asset — one per user per
    asset. Separate from AssetModerationStatus: a like is informal feedback
    from anyone with access (brand or admin), not the formal approve/reject
    decision that actually gates the influencer broadcast.
    """

    __tablename__ = "asset_likes"
    __table_args__ = (UniqueConstraint("asset_id", "user_id", name="uq_asset_like_per_user"),)

    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("advertisement_assets.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
