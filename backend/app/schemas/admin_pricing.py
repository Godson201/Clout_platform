import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SocialPlatform


class ViewRateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    platform: SocialPlatform
    rate_per_view: Decimal
    currency: str
    updated_at: datetime


class ViewRateUpsert(BaseModel):
    platform: SocialPlatform
    rate_per_view: Decimal = Field(gt=0)
    currency: str = Field(default="RWF", min_length=3, max_length=3)


class FeeConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    brand_fee_pct: Decimal
    influencer_fee_pct: Decimal
    updated_at: datetime


class FeeConfigUpdate(BaseModel):
    brand_fee_pct: Decimal | None = Field(default=None, ge=0, le=1)
    influencer_fee_pct: Decimal | None = Field(default=None, ge=0, le=1)
