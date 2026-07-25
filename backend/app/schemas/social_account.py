import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import SocialAccountStatus, SocialPlatform


class ConnectResponse(BaseModel):
    authorization_url: str


class OAuthCallbackRequest(BaseModel):
    code: str = Field(min_length=1)
    state: str = Field(min_length=1)


class SocialAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    platform: SocialPlatform
    external_account_id: str
    handle: str
    scopes: list[str]
    status: SocialAccountStatus
    token_expires_at: datetime | None
    created_at: datetime
