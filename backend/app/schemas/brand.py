import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import VerificationStatus


class BrandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_name: str
    sector: str | None
    location: str | None
    description: str | None
    website: str | None
    logo_url: str | None
    contact_phone: str | None
    contact_email: EmailStr | None
    verification_status: VerificationStatus
    created_at: datetime


class BrandUpdate(BaseModel):
    business_name: str | None = None
    sector: str | None = None
    location: str | None = None
    description: str | None = None
    website: str | None = None
    logo_url: str | None = None
    contact_phone: str | None = None
    contact_email: EmailStr | None = None
