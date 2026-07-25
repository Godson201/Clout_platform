import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import UserType


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    phone_number: str | None
    user_type: UserType
    is_active: bool
    is_verified: bool
    created_at: datetime
    roles: list[str] = []

    @classmethod
    def from_orm_user(cls, user) -> "UserRead":
        return cls(
            id=user.id,
            email=user.email,
            phone_number=user.phone_number,
            user_type=user.user_type,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            roles=user.role_names,
        )
