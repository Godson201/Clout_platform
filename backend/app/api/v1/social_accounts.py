import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.enums import SocialPlatform
from app.models.social_account import SocialAccount
from app.models.user import User
from app.schemas.social_account import ConnectResponse, OAuthCallbackRequest, SocialAccountRead
from app.services.social_accounts import complete_connection, disconnect_account, initiate_connection

router = APIRouter(prefix="/social-accounts", tags=["social-accounts"])


@router.get("/connect/{platform}", response_model=ConnectResponse)
async def connect_platform(
    platform: SocialPlatform, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> ConnectResponse:
    """Available to both brands and influencers — the product spec has brands
    optionally connecting their own accounts too, not just influencers."""
    url = await initiate_connection(db, user=user, platform=platform)
    return ConnectResponse(authorization_url=url)


@router.post("/callback/{platform}", response_model=SocialAccountRead, status_code=status.HTTP_201_CREATED)
async def oauth_callback(
    platform: SocialPlatform,
    payload: OAuthCallbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SocialAccountRead:
    """The frontend's callback page calls this after the provider redirects the
    user's browser back with ?code=...&state=... in the URL."""
    account = await complete_connection(db, user=user, platform=platform, code=payload.code, state=payload.state)
    return SocialAccountRead.model_validate(account)


@router.get("/me", response_model=list[SocialAccountRead])
async def list_my_social_accounts(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> list[SocialAccountRead]:
    result = await db.execute(select(SocialAccount).where(SocialAccount.owner_user_id == user.id))
    return [SocialAccountRead.model_validate(a) for a in result.scalars().all()]


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_social_account(
    account_id: uuid.UUID, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> None:
    result = await db.execute(
        select(SocialAccount).where(SocialAccount.id == account_id, SocialAccount.owner_user_id == user.id)
    )
    account = result.scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Social account not found")

    await disconnect_account(db, user=user, account=account)
