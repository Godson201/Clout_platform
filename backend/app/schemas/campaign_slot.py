import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import FollowerTier, SlotStatus, SocialPlatform
from app.schemas.campaign import CampaignRead


class CampaignSlotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    campaign_id: uuid.UUID
    platform: SocialPlatform
    tier: FollowerTier
    target_views: int
    budget_allocated: Decimal
    status: SlotStatus
    influencer_id: uuid.UUID | None
    claimed_at: datetime | None
    created_at: datetime
    delivered_pct: Decimal | None
    recovered_from_slot_id: uuid.UUID | None
    recovery_generation: int


class CampaignDetailRead(CampaignRead):
    slots: list[CampaignSlotRead] = []
    escrow_balance: Decimal | None = None


class MatchScoreBreakdownRead(BaseModel):
    sector_score: float
    location_score: float
    tier_score: float
    reliability_score: float
    platform_score: float
    engagement_score: float
    total: float


class MarketplaceSlotRead(CampaignSlotRead):
    brand_name: str
    advertisement_title: str
    campaign_target_sector: str | None
    campaign_target_location: str | None
    match_score: MatchScoreBreakdownRead
    historical_boost: float
    final_score: float


class MySlotRead(CampaignSlotRead):
    brand_id: uuid.UUID
    brand_name: str
    advertisement_title: str
