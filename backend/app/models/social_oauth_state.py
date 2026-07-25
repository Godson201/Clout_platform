import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import SocialPlatform
from app.models.mixins import UUIDPk


class SocialOAuthState(UUIDPk, Base):
    """A short-lived, single-use record of a pending OAuth authorization request
    — CSRF-protects the flow (the `state` value must round-trip unmodified
    through the provider's redirect) and carries the PKCE code_verifier
    (TikTok) and the exact redirect_uri used, both of which the token-exchange
    call needs but which never travel through the browser.
    """

    __tablename__ = "social_oauth_states"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    platform: Mapped[SocialPlatform] = mapped_column(
        Enum(SocialPlatform, name="social_platform", values_callable=lambda e: [m.value for m in e])
    )
    state: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    code_verifier: Mapped[str | None] = mapped_column(String(128), default=None)
    redirect_uri: Mapped[str] = mapped_column(String(512))

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
