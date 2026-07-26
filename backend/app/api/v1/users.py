from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest
from app.schemas.user import UserRead
from app.services import auth as auth_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def get_me(user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.from_orm_user(user)


@router.post("/me/change-password", status_code=status.HTTP_200_OK)
async def change_my_password(
    payload: ChangePasswordRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    await auth_service.change_password(
        db, user=user, current_password=payload.current_password, new_password=payload.new_password
    )
    return {"detail": "Password updated"}
