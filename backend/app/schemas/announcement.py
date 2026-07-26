import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import AnnouncementAudience


class AnnouncementRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    title: str
    body: str
    audience: AnnouncementAudience
    is_active: bool
    created_at: datetime


class AnnouncementCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    body: str = Field(min_length=2, max_length=5000)
    audience: AnnouncementAudience = AnnouncementAudience.ALL


class AnnouncementUpdateRequest(BaseModel):
    is_active: bool
