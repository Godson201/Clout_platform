from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import (
    AccessTokenResponse,
    BrandRegisterRequest,
    ForgotPasswordRequest,
    InfluencerRegisterRequest,
    LoginRequest,
    PasswordResetPromptResponse,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from app.schemas.user import UserRead
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

REFRESH_COOKIE_NAME = "clout_refresh_token"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, raw_token: str, expires_at) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
        expires=int(expires_at.timestamp()),
    )


@router.post("/register/brand", response_model=AccessTokenResponse, status_code=status.HTTP_201_CREATED)
async def register_brand(
    payload: BrandRegisterRequest, response: Response, db: AsyncSession = Depends(get_db)
) -> AccessTokenResponse:
    user = await auth_service.register_brand(db, payload)
    access_token = auth_service.issue_access_token(user)
    raw_refresh, expires_at = await auth_service.issue_refresh_token(db, user)
    _set_refresh_cookie(response, raw_refresh, expires_at)
    return AccessTokenResponse(access_token=access_token, user=UserRead.from_orm_user(user))


@router.post("/register/influencer", response_model=AccessTokenResponse, status_code=status.HTTP_201_CREATED)
async def register_influencer(
    payload: InfluencerRegisterRequest, response: Response, db: AsyncSession = Depends(get_db)
) -> AccessTokenResponse:
    user = await auth_service.register_influencer(db, payload)
    access_token = auth_service.issue_access_token(user)
    raw_refresh, expires_at = await auth_service.issue_refresh_token(db, user)
    _set_refresh_cookie(response, raw_refresh, expires_at)
    return AccessTokenResponse(access_token=access_token, user=UserRead.from_orm_user(user))


@router.post("/login", response_model=AccessTokenResponse)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)) -> AccessTokenResponse:
    user = await auth_service.authenticate_user(db, payload.email, payload.password)
    access_token = auth_service.issue_access_token(user)
    raw_refresh, expires_at = await auth_service.issue_refresh_token(db, user)
    _set_refresh_cookie(response, raw_refresh, expires_at)
    return AccessTokenResponse(access_token=access_token, user=UserRead.from_orm_user(user))


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    response: Response,
    clout_refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> AccessTokenResponse:
    if clout_refresh_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token provided")

    user, new_raw, new_expires = await auth_service.rotate_refresh_token(db, clout_refresh_token)
    access_token = auth_service.issue_access_token(user)
    _set_refresh_cookie(response, new_raw, new_expires)
    return AccessTokenResponse(access_token=access_token, user=UserRead.from_orm_user(user))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    clout_refresh_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> None:
    if clout_refresh_token is not None:
        await auth_service.revoke_refresh_token(db, clout_refresh_token)
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(payload: VerifyEmailRequest, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    await auth_service.verify_email(db, payload.token)
    return {"detail": "Email verified"}


@router.post("/resend-verification", status_code=status.HTTP_200_OK)
async def resend_verification(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    await auth_service.resend_verification_email(db, user)
    return {"detail": "Verification email sent"}


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    # Always returns the same message whether or not the email is registered —
    # otherwise this endpoint becomes a way to check who has an account.
    await auth_service.request_password_reset(db, payload.email)
    return {"detail": "If that email is registered, a password reset link has been sent."}


@router.get("/reset-password/{token}", response_model=PasswordResetPromptResponse)
async def get_reset_password_prompt(token: str, db: AsyncSession = Depends(get_db)) -> PasswordResetPromptResponse:
    question = await auth_service.get_password_reset_prompt(db, token)
    return PasswordResetPromptResponse(security_question=question)


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    await auth_service.reset_password(
        db, raw_token=payload.token, new_password=payload.new_password, security_answer=payload.security_answer
    )
    return {"detail": "Password updated"}
