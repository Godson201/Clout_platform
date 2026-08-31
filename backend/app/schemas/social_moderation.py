import uuid
from datetime import datetime
from pydantic import BaseModel, Field

class SocialReportQueueItem(BaseModel):
    report_id: uuid.UUID
    post_id: uuid.UUID
    author_id: uuid.UUID
    body: str
    reason: str
    details: str | None
    created_at: datetime

class ModerationDecision(BaseModel):
    archive_post: bool = False
    note: str | None = Field(default=None, max_length=1000)
