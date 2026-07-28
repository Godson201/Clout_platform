import uuid

from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationType, UserType
from app.models.notification import Notification
from app.models.user import User


def _row(user_id: uuid.UUID, type_: NotificationType, title: str, body: str, link: str | None, data: dict) -> dict:
    return {
        "id": uuid.uuid4(),
        "user_id": user_id,
        "type": type_,
        "title": title,
        "body": body,
        "link": link,
        "data": data or {},
    }


async def notify_user(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    type_: NotificationType,
    title: str,
    body: str,
    link: str | None = None,
    data: dict | None = None,
) -> None:
    await db.execute(insert(Notification), [_row(user_id, type_, title, body, link, data or {})])
    await db.commit()


async def notify_all_influencers(
    db: AsyncSession,
    *,
    type_: NotificationType,
    title: str,
    body: str,
    link: str | None = None,
    data: dict | None = None,
) -> None:
    result = await db.execute(select(User.id).where(User.user_type == UserType.INFLUENCER, User.is_active.is_(True)))
    user_ids = result.scalars().all()
    if not user_ids:
        return
    rows = [_row(uid, type_, title, body, link, data or {}) for uid in user_ids]
    await db.execute(insert(Notification), rows)
    await db.commit()


async def list_notifications_for_user(db: AsyncSession, *, user_id: uuid.UUID, limit: int = 50) -> list[Notification]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def unread_count_for_user(db: AsyncSession, *, user_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count()).select_from(Notification).where(Notification.user_id == user_id, Notification.is_read.is_(False))
    )
    return result.scalar_one()


async def mark_notification_read(db: AsyncSession, *, user_id: uuid.UUID, notification_id: uuid.UUID) -> None:
    await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == user_id)
        .values(is_read=True)
    )
    await db.commit()


async def mark_all_notifications_read(db: AsyncSession, *, user_id: uuid.UUID) -> None:
    await db.execute(
        update(Notification).where(Notification.user_id == user_id, Notification.is_read.is_(False)).values(is_read=True)
    )
    await db.commit()
