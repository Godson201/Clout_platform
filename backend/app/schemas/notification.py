import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import NotificationType


class NotificationRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    type: NotificationType
    title: str
    body: str
    link: str | None
    data: dict
    is_read: bool
    created_at: datetime


class UnreadCountRead(BaseModel):
    unread_count: int
