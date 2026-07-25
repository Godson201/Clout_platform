import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import FollowerTier, VerificationStatus


class InfluencerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str
    username: str
    location: str | None
    sector: str | None
    bio: str | None
    follower_tier: FollowerTier | None
    estimated_followers: int | None
    completed_slots_count: int
    failed_slots_count: int
    verification_status: VerificationStatus
    created_at: datetime


class InfluencerUpdate(BaseModel):
    display_name: str | None = None
    location: str | None = None
    sector: str | None = None
    bio: str | None = None
    follower_tier: FollowerTier | None = None
    estimated_followers: int | None = None
