import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PaymentProvider, PaymentStatus


class PayoutRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    phone_number: str = Field(min_length=6, max_length=32)


class PayoutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    influencer_id: uuid.UUID
    provider: PaymentProvider
    provider_reference: str
    phone_number: str
    amount: Decimal
    fee_pct: Decimal
    fee_amount: Decimal
    net_amount: Decimal
    currency: str
    status: PaymentStatus
    failure_reason: str | None
    completed_at: datetime | None
    created_at: datetime
