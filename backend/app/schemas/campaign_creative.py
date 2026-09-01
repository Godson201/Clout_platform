import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CampaignCreativeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    campaign_slot_id: uuid.UUID
    influencer_id: uuid.UUID
    original_filename: str
    mime_type: str
    duration_seconds: float
    native_post_id: uuid.UUID | None
    url: str
    created_at: datetime
    updated_at: datetime


class PublishCampaignCreativeRequest(BaseModel):
    caption: str = Field(min_length=1, max_length=5000)


class CampaignCreativePublicationRead(BaseModel):
    native_post_id: uuid.UUID
    caption: str
    feed_path: str
