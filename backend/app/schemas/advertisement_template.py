import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AdvertisementTemplateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    category: str
    description: str | None
    default_duration_seconds: int
    is_active: bool
    created_at: datetime


class AdvertisementTemplateCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=2, max_length=128)
    category: str = Field(min_length=2, max_length=64)
    description: str | None = None
    default_duration_seconds: int = Field(default=30, ge=5, le=180)


class AdvertisementTemplateUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    default_duration_seconds: int | None = Field(default=None, ge=5, le=180)
    is_active: bool | None = None
