import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import CampaignStatus, FollowerTier, SocialPlatform


class CampaignCreate(BaseModel):
    advertisement_id: uuid.UUID
    platforms: list[SocialPlatform] = Field(min_length=1)
    target_views: int = Field(gt=0)
    tier: FollowerTier
    slot_count: int = Field(gt=0, le=50)
    performance_window_days: int = Field(default=3, ge=1, le=30)
    target_sector: str | None = None
    target_location: str | None = None

    @field_validator("platforms")
    @classmethod
    def _dedupe_platforms(cls, v: list[SocialPlatform]) -> list[SocialPlatform]:
        deduped = list(dict.fromkeys(v))
        if not deduped:
            raise ValueError("At least one platform is required")
        return deduped


class CampaignRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    brand_id: uuid.UUID
    advertisement_id: uuid.UUID
    status: CampaignStatus
    platforms: list[str]
    target_views: int
    tier: FollowerTier
    slot_count: int
    performance_window_days: int
    target_sector: str | None
    target_location: str | None
    rate_snapshot: dict[str, str]
    brand_fee_pct: Decimal
    base_price: Decimal
    total_brand_payment: Decimal
    currency: str
    created_at: datetime
    updated_at: datetime
