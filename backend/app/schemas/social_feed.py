import uuid
from datetime import datetime

from pydantic import BaseModel, Field
from app.models.enums import NativePostVisibility, SocialPlatform, SocialPostStatus


class CreatePostRequest(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    visibility: NativePostVisibility = NativePostVisibility.PUBLIC


class CreateCommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class ReportPostRequest(BaseModel):
    reason: str = Field(min_length=2, max_length=64)
    details: str | None = Field(default=None, max_length=1000)


class SocialAuthor(BaseModel):
    id: uuid.UUID
    name: str
    username: str | None = None
    picture_url: str | None = None


class SocialCommentRead(BaseModel):
    id: uuid.UUID
    body: str
    created_at: datetime
    author: SocialAuthor


class SocialPostRead(BaseModel):
    id: uuid.UUID
    body: str
    created_at: datetime
    author: SocialAuthor
    like_count: int
    comment_count: int
    liked_by_me: bool
    saved_by_me: bool
    media: list["SocialMediaRead"] = []
    hashtags: list[str] = []
    repost_of_id: uuid.UUID | None = None
    visibility: NativePostVisibility


class SocialMediaRead(BaseModel):
    id: uuid.UUID
    media_type: str
    mime_type: str
    url: str
    processing_status: str
    thumbnail_url: str | None = None


class CrossPostRequest(BaseModel):
    social_account_ids: list[uuid.UUID] = Field(min_length=1, max_length=4)


class CrossPostRead(BaseModel):
    id: uuid.UUID
    social_account_id: uuid.UUID
    platform: SocialPlatform
    status: SocialPostStatus
    post_url: str | None
    error_message: str | None


class FollowStatusRead(BaseModel):
    following: bool
    follower_count: int
    following_count: int


class SocialProfileRead(BaseModel):
    author: SocialAuthor
    follower_count: int
    following_count: int
    following_by_me: bool
    posts: list[SocialPostRead] = []


class SocialProfileListRead(BaseModel):
    items: list[SocialAuthor]
    total: int
