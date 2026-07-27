import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.notification import NotificationRead, UnreadCountRead
from app.services.notifications import (
    list_notifications_for_user,
    mark_all_notifications_read,
    mark_notification_read,
    unread_count_for_user,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
async def list_notifications(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[NotificationRead]:
    notifications = await list_notifications_for_user(db, user_id=user.id)
    return [NotificationRead.model_validate(n) for n in notifications]


@router.get("/unread-count", response_model=UnreadCountRead)
async def get_unread_count(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> UnreadCountRead:
    count = await unread_count_for_user(db, user_id=user.id)
    return UnreadCountRead(unread_count=count)


@router.post("/{notification_id}/read", status_code=204)
async def mark_read(
    notification_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    await mark_notification_read(db, user_id=user.id, notification_id=notification_id)


@router.post("/read-all", status_code=204)
async def mark_all_read(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)) -> None:
    await mark_all_notifications_read(db, user_id=user.id)
