from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.enums import UserType
from app.models.mixins import UUIDPk


class OAuthLoginState(UUIDPk, Base):
    """A short-lived, single-use record of a pending "Sign in with Google"
    (etc.) attempt — CSRF-protects the flow (the `state` value must round-trip
    unmodified through the provider's redirect) the same way SocialOAuthState
    does for connecting a platform, but this one exists *before* anyone is
    authenticated, so it has no `user_id` — instead it carries `user_type`,
    the hint chosen on the register page for a brand-new account (None for
    the login page, where the account, if any, is looked up instead).
    """

    __tablename__ = "oauth_login_states"

    provider: Mapped[str] = mapped_column(String(32))
    state: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    user_type: Mapped[UserType | None] = mapped_column(
        Enum(UserType, name="user_type", values_callable=lambda e: [m.value for m in e]), default=None
    )
    redirect_uri: Mapped[str] = mapped_column(String(512))

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
