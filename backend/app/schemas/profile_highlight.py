import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models.enums import HighlightCategory


class ProfileHighlightRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    category: HighlightCategory
    title: str
    subtitle: str | None
    occurred_on: date | None
    description: str | None
    created_at: datetime


class ProfileHighlightCreateRequest(BaseModel):
    category: HighlightCategory
    title: str = Field(min_length=1, max_length=255)
    subtitle: str | None = Field(default=None, max_length=255)
    occurred_on: date | None = None
    description: str | None = Field(default=None, max_length=2000)
