import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AssetCommentRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    asset_id: uuid.UUID
    author_user_id: uuid.UUID
    author_name: str
    author_is_admin: bool
    body: str
    created_at: datetime


class CreateAssetCommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class AssetLikeStatusRead(BaseModel):
    liked: bool
    like_count: int
