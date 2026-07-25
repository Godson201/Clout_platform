import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PaymentProvider, PaymentStatus


class FundCampaignRequest(BaseModel):
    phone_number: str = Field(min_length=6, max_length=32)


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    campaign_id: uuid.UUID
    provider: PaymentProvider
    provider_reference: str
    phone_number: str
    amount: Decimal
    currency: str
    status: PaymentStatus
    failure_reason: str | None
    confirmed_at: datetime | None
    created_at: datetime


class MoMoWebhookPayload(BaseModel):
    """Shape we expect from MTN MoMo's callback — a client-generated reference
    plus the provider's resulting status. Real MoMo callbacks vary by product
    (collections vs disbursements) and this is deliberately loose (`status` as a
    free string, mapped defensively) rather than modeling MoMo's full schema,
    since sandbox docs and production payloads have historically drifted.
    """

    referenceId: str
    status: str
    reason: str | None = None
