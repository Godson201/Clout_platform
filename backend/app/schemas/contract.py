import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ContractStatus


class ContractRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    brand_id: uuid.UUID
    influencer_id: uuid.UUID
    campaign_id: uuid.UUID | None
    title: str
    terms_text: str
    status: ContractStatus
    proposed_by_user_id: uuid.UUID
    responded_by_user_id: uuid.UUID | None
    responded_at: datetime | None
    created_at: datetime


class ProposeContractRequest(BaseModel):
    counterpart_id: uuid.UUID
    campaign_id: uuid.UUID | None = None
    title: str = Field(min_length=2, max_length=255)
    terms_text: str = Field(min_length=10, max_length=10_000)


class AdminContractRead(ContractRead):
    brand_name: str
    influencer_username: str
