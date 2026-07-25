from pydantic import BaseModel

from app.models.enums import VerificationStatus


class UserStatusUpdate(BaseModel):
    is_active: bool


class VerificationDecision(BaseModel):
    status: VerificationStatus
    reason: str | None = None
