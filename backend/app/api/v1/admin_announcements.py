import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import require_admin
from app.models.announcement import Announcement
from app.models.user import User
from app.schemas.announcement import AnnouncementCreateRequest, AnnouncementRead, AnnouncementUpdateRequest

router = APIRouter(prefix="/admin/announcements", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("", response_model=list[AnnouncementRead])
async def list_all_announcements(db: AsyncSession = Depends(get_db)) -> list[AnnouncementRead]:
    result = await db.execute(select(Announcement).order_by(Announcement.created_at.desc()))
    return [AnnouncementRead.model_validate(a) for a in result.scalars().all()]


@router.post("", response_model=AnnouncementRead, status_code=status.HTTP_201_CREATED)
async def create_announcement(
    payload: AnnouncementCreateRequest, admin: User = Depends(require_admin), db: AsyncSession = Depends(get_db)
) -> AnnouncementRead:
    announcement = Announcement(
        author_admin_id=admin.id, title=payload.title, body=payload.body, audience=payload.audience
    )
    db.add(announcement)
    await db.commit()
    await db.refresh(announcement)
    return AnnouncementRead.model_validate(announcement)


@router.patch("/{announcement_id}", response_model=AnnouncementRead)
async def update_announcement(
    announcement_id: uuid.UUID, payload: AnnouncementUpdateRequest, db: AsyncSession = Depends(get_db)
) -> AnnouncementRead:
    announcement = await db.get(Announcement, announcement_id)
    if announcement is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")

    announcement.is_active = payload.is_active
    await db.commit()
    await db.refresh(announcement)
    return AnnouncementRead.model_validate(announcement)
