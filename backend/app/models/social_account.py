import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import SocialAccountStatus, SocialPlatform
from app.models.mixins import TimestampMixin, UUIDPk


class SocialAccount(UUIDPk, TimestampMixin, Base):
    """A connected social account — brand or influencer, one per platform per
    user for now (multiple accounts on the same platform is a later
    enhancement). Tokens are stored only in encrypted form (see
    app/core/crypto.py); nothing here is ever logged or returned over the API.
    """

    __tablename__ = "social_accounts"
    __table_args__ = (UniqueConstraint("owner_user_id", "platform", name="uq_social_account_owner_platform"),)

    owner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    platform: Mapped[SocialPlatform] = mapped_column(
        Enum(SocialPlatform, name="social_platform", values_callable=lambda e: [m.value for m in e])
    )

    external_account_id: Mapped[str] = mapped_column(String(128))
    handle: Mapped[str] = mapped_column(String(255))

    access_token_encrypted: Mapped[str] = mapped_column(Text)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, default=None)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    scopes: Mapped[list[str]] = mapped_column(JSON, default=list)

    status: Mapped[SocialAccountStatus] = mapped_column(
        Enum(SocialAccountStatus, name="social_account_status", values_callable=lambda e: [m.value for m in e]),
        default=SocialAccountStatus.ACTIVE,
    )
