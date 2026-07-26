import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr

from app.models.enums import VerificationStatus


class BrandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_name: str
    sector: str | None
    province: str | None
    location: str | None
    admin_sector: str | None
    admin_cell: str | None
    admin_village: str | None
    address_detail: str | None
    description: str | None
    legacy: str | None
    website: str | None
    logo_url: str | None
    contact_phone: str | None
    contact_email: EmailStr | None
    verification_status: VerificationStatus
    visibility_settings: dict[str, bool]
    created_at: datetime


class BrandUpdate(BaseModel):
    business_name: str | None = None
    sector: str | None = None
    province: str | None = None
    location: str | None = None
    admin_sector: str | None = None
    admin_cell: str | None = None
    admin_village: str | None = None
    address_detail: str | None = None
    description: str | None = None
    legacy: str | None = None
    website: str | None = None
    logo_url: str | None = None
    contact_phone: str | None = None
    contact_email: EmailStr | None = None
    visibility_settings: dict[str, bool] | None = None
