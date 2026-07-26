from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.announcement import Announcement
from app.models.enums import AnnouncementAudience, UserType
from app.models.user import User
from app.schemas.announcement import AnnouncementRead

router = APIRouter(prefix="/announcements", tags=["announcements"])

_AUDIENCE_BY_USER_TYPE = {
    UserType.BRAND: AnnouncementAudience.BRANDS,
    UserType.INFLUENCER: AnnouncementAudience.INFLUENCERS,
}


@router.get("", response_model=list[AnnouncementRead])
async def list_announcements(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[AnnouncementRead]:
    my_audience = _AUDIENCE_BY_USER_TYPE.get(user.user_type)
    stmt = select(Announcement).where(Announcement.is_active.is_(True)).order_by(Announcement.created_at.desc())
    if my_audience is not None:
        stmt = stmt.where(or_(Announcement.audience == AnnouncementAudience.ALL, Announcement.audience == my_audience))
    else:
        stmt = stmt.where(Announcement.audience == AnnouncementAudience.ALL)

    result = await db.execute(stmt)
    return [AnnouncementRead.model_validate(a) for a in result.scalars().all()]
