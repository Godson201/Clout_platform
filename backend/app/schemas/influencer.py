import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import FollowerTier, VerificationStatus


class InfluencerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str
    username: str
    province: str | None
    location: str | None
    admin_sector: str | None
    admin_cell: str | None
    admin_village: str | None
    address_detail: str | None
    sector: str | None
    bio: str | None
    legacy: str | None
    profile_picture_url: str | None
    follower_tier: FollowerTier | None
    estimated_followers: int | None
    completed_slots_count: int
    failed_slots_count: int
    verification_status: VerificationStatus
    visibility_settings: dict[str, bool]
    created_at: datetime


class InfluencerUpdate(BaseModel):
    display_name: str | None = None
    province: str | None = None
    location: str | None = None
    admin_sector: str | None = None
    admin_cell: str | None = None
    admin_village: str | None = None
    address_detail: str | None = None
    sector: str | None = None
    bio: str | None = None
    legacy: str | None = None
    follower_tier: FollowerTier | None = None
    estimated_followers: int | None = None
    visibility_settings: dict[str, bool] | None = None
