from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.enums import UserType
from app.models.mixins import TimestampMixin, UUIDPk
from app.models.rbac import Role, user_roles

if TYPE_CHECKING:
    from app.models.brand import Brand
    from app.models.influencer import Influencer


class User(UUIDPk, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone_number: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, default=None)
    hashed_password: Mapped[str] = mapped_column(String(255))

    user_type: Mapped[UserType] = mapped_column(Enum(UserType, name="user_type", values_callable=lambda e: [m.value for m in e]))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Optional (nullable for accounts created before this existed): a fallback
    # identity check for password reset, used alongside — not instead of —
    # emailed-link possession. The answer is hashed the same way a password is,
    # never stored or returned in plaintext.
    security_question: Mapped[str | None] = mapped_column(String(255), default=None)
    security_answer_hash: Mapped[str | None] = mapped_column(String(255), default=None)

    roles: Mapped[list[Role]] = relationship(secondary=user_roles, back_populates="users")

    brand: Mapped["Brand | None"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    influencer: Mapped["Influencer | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def role_names(self) -> list[str]:
        return [r.name for r in self.roles]
