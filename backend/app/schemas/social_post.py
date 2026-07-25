import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PublishMode, SocialPlatform, SocialPostStatus


class CreatePostRequest(BaseModel):
    social_account_id: uuid.UUID
    caption: str = Field(min_length=1, max_length=2200)


class SubmitPostUrlRequest(BaseModel):
    post_url: str = Field(min_length=1, max_length=1024)


class SocialPostRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    campaign_slot_id: uuid.UUID
    social_account_id: uuid.UUID | None
    platform: SocialPlatform
    publish_mode: PublishMode
    caption: str
    external_post_id: str | None
    post_url: str | None
    status: SocialPostStatus
    published_at: datetime | None
    created_at: datetime


class PostMetricSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    views: int
    likes: int
    comments: int
    shares: int | None
    fetched_at: datetime
