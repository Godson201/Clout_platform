import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CreatePostRequest(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class CreateCommentRequest(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


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


class SocialMediaRead(BaseModel):
    id: uuid.UUID
    media_type: str
    mime_type: str
    url: str


class FollowStatusRead(BaseModel):
    following: bool
    follower_count: int
    following_count: int
