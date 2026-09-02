import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AdvertisementStatus, AssetDistribution, AssetModerationStatus, AssetStatus, AssetType, RenditionStatus, SocialPlatform


class AdvertisementRenditionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    platform: SocialPlatform
    status: RenditionStatus
    width: int | None
    height: int | None
    duration_seconds: float | None
    error_message: str | None
    url: str | None = None


class AdvertisementAssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_type: AssetType
    original_filename: str
    mime_type: str
    file_size_bytes: int
    duration_seconds: float | None
    width: int | None
    height: int | None
    status: AssetStatus
    error_message: str | None
    created_at: datetime
    url: str | None = None
    renditions: list[AdvertisementRenditionRead] = []
    moderation_status: AssetModerationStatus
    moderation_note: str | None = None
    distribution: AssetDistribution
    recipient_influencer_ids: list[uuid.UUID] = []


class AssetDistributionUpdate(BaseModel):
    distribution: AssetDistribution
    recipient_influencer_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)


class InfluencerAudienceOption(BaseModel):
    id: uuid.UUID
    display_name: str
    username: str
    sector: str | None
    location: str | None
    follower_tier: str | None


class AdvertisementCreate(BaseModel):
    template_id: uuid.UUID
    title: str = Field(min_length=2, max_length=255)
    script_text: str | None = None
    cta_text: str | None = Field(default=None, max_length=255)
    hashtags: list[str] = []
    duration_seconds: int | None = Field(default=None, ge=5, le=180)


class AdvertisementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    script_text: str | None = None
    cta_text: str | None = Field(default=None, max_length=255)
    hashtags: list[str] | None = None
    duration_seconds: int | None = Field(default=None, ge=5, le=180)
    status: AdvertisementStatus | None = None


class AdvertisementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    brand_id: uuid.UUID
    template_id: uuid.UUID
    title: str
    status: AdvertisementStatus
    script_text: str | None
    cta_text: str | None
    hashtags: list[str]
    duration_seconds: int | None
    created_at: datetime
    updated_at: datetime


class AdvertisementDetailRead(AdvertisementRead):
    assets: list[AdvertisementAssetRead] = []


class AssetModerationQueueItem(AdvertisementAssetRead):
    advertisement_id: uuid.UUID
    advertisement_title: str
    brand_name: str
    campaign_brief: str | None = None
    cta_text: str | None = None
    campaign_slot_id: uuid.UUID | None = None
    campaign_slot_status: str | None = None


class RejectAssetRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=1000)
