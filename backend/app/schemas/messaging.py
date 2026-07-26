import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import MessageType


class CounterpartRead(BaseModel):
    user_id: uuid.UUID
    name: str
    picture_url: str | None


class MessageRead(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_user_id: uuid.UUID
    is_mine: bool
    message_type: MessageType
    text_body: str | None
    attachment_url: str | None
    attachment_original_filename: str | None
    attachment_mime_type: str | None
    attachment_size_bytes: int | None
    created_at: datetime
    read_at: datetime | None


class ConversationRead(BaseModel):
    id: uuid.UUID
    counterpart: CounterpartRead
    last_message: MessageRead | None
    unread_count: int
    last_message_at: datetime


class StartConversationRequest(BaseModel):
    counterpart_id: uuid.UUID


class SendTextMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
