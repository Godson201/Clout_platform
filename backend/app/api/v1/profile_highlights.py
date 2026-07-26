import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.enums import ProfileOwnerType, UserType
from app.models.profile_highlight import ProfileHighlight
from app.models.user import User
from app.schemas.profile_highlight import ProfileHighlightCreateRequest, ProfileHighlightRead

router = APIRouter(prefix="/profile-highlights", tags=["profile-highlights"])

_OWNER_TYPE_BY_USER_TYPE = {UserType.BRAND: ProfileOwnerType.BRAND, UserType.INFLUENCER: ProfileOwnerType.INFLUENCER}


def _owner_type_for(user: User) -> ProfileOwnerType:
    owner_type = _OWNER_TYPE_BY_USER_TYPE.get(user.user_type)
    if owner_type is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only brands and influencers have profile highlights")
    return owner_type


@router.get("/me", response_model=list[ProfileHighlightRead])
async def list_my_highlights(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[ProfileHighlightRead]:
    owner_type = _owner_type_for(user)
    result = await db.execute(
        select(ProfileHighlight)
        .where(ProfileHighlight.owner_type == owner_type, ProfileHighlight.owner_id == user.id)
        .order_by(ProfileHighlight.occurred_on.desc().nulls_last(), ProfileHighlight.created_at.desc())
    )
    return [ProfileHighlightRead.model_validate(h) for h in result.scalars().all()]


@router.post("", response_model=ProfileHighlightRead, status_code=status.HTTP_201_CREATED)
async def create_highlight(
    payload: ProfileHighlightCreateRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ProfileHighlightRead:
    owner_type = _owner_type_for(user)
    highlight = ProfileHighlight(
        owner_type=owner_type,
        owner_id=user.id,
        category=payload.category,
        title=payload.title,
        subtitle=payload.subtitle,
        occurred_on=payload.occurred_on,
        description=payload.description,
    )
    db.add(highlight)
    await db.commit()
    await db.refresh(highlight)
    return ProfileHighlightRead.model_validate(highlight)


@router.delete("/{highlight_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_highlight(
    highlight_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    owner_type = _owner_type_for(user)
    highlight = await db.get(ProfileHighlight, highlight_id)
    if highlight is None or highlight.owner_type != owner_type or highlight.owner_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Highlight not found")

    await db.delete(highlight)
    await db.commit()
