import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import FollowerTier, SlotStatus, SocialPlatform


class SlotSettlementRequest(BaseModel):
    delivered_pct: Decimal = Field(ge=0, le=100)


class AwaitingSettlementItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slot_id: uuid.UUID
    campaign_id: uuid.UUID
    platform: SocialPlatform
    tier: FollowerTier
    status: SlotStatus
    target_views: int
    budget_allocated: Decimal
    brand_name: str
    influencer_username: str
    post_url: str | None
    published_at: datetime | None
    window_closed_at: datetime
