from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import (
    as_aware_utc,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.brand import Brand
from app.models.enums import UserType, WalletOwnerType
from app.models.influencer import Influencer
from app.models.rbac import Role
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import BrandRegisterRequest, InfluencerRegisterRequest
from app.services.audit import write_audit_log
from app.services.wallet import create_wallet_for_owner


async def _get_role(db: AsyncSession, name: str) -> Role:
    result = await db.execute(select(Role).where(Role.name == name))
    role = result.scalar_one_or_none()
    if role is None:
        raise RuntimeError(f"Role '{name}' is not seeded. Run the seed script before starting the API.")
    return role


async def register_brand(db: AsyncSession, payload: BrandRegisterRequest) -> User:
    role = await _get_role(db, "brand")

    user = User(
        email=payload.email.lower(),
        phone_number=payload.phone_number,
        hashed_password=hash_password(payload.password),
        user_type=UserType.BRAND,
    )
    user.roles.append(role)
    db.add(user)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email or phone number already registered")

    brand = Brand(
        id=user.id,
        business_name=payload.business_name,
        sector=payload.sector,
        location=payload.location,
        contact_email=payload.email.lower(),
        contact_phone=payload.phone_number,
    )
    db.add(brand)

    await create_wallet_for_owner(db, owner_type=WalletOwnerType.BRAND, owner_id=user.id)
    await write_audit_log(db, actor_user_id=user.id, action="user.register", entity_type="user", entity_id=user.id)

    await db.commit()

    result = await db.execute(select(User).options(selectinload(User.roles)).where(User.id == user.id))
    return result.scalar_one()


async def register_influencer(db: AsyncSession, payload: InfluencerRegisterRequest) -> User:
    role = await _get_role(db, "influencer")

    user = User(
        email=payload.email.lower(),
        phone_number=payload.phone_number,
        hashed_password=hash_password(payload.password),
        user_type=UserType.INFLUENCER,
    )
    user.roles.append(role)
    db.add(user)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email, phone number, or username already registered"
        )

    influencer = Influencer(
        id=user.id,
        display_name=payload.display_name,
        username=payload.username.lower(),
        location=payload.location,
        sector=payload.sector,
    )
    db.add(influencer)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

    await create_wallet_for_owner(db, owner_type=WalletOwnerType.INFLUENCER, owner_id=user.id)
    await write_audit_log(db, actor_user_id=user.id, action="user.register", entity_type="user", entity_id=user.id)

    await db.commit()

    result = await db.execute(select(User).options(selectinload(User.roles)).where(User.id == user.id))
    return result.scalar_one()


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User:
    result = await db.execute(select(User).options(selectinload(User.roles)).where(User.email == email.lower()))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    return user


def issue_access_token(user: User) -> str:
    return create_access_token(user_id=user.id, user_type=user.user_type.value, roles=user.role_names)


async def issue_refresh_token(db: AsyncSession, user: User) -> tuple[str, datetime]:
    raw, token_hash, expires_at = generate_refresh_token()
    db.add(RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=expires_at))
    await db.commit()
    return raw, expires_at


async def rotate_refresh_token(db: AsyncSession, raw_token: str) -> tuple[User, str, datetime]:
    token_hash = hash_refresh_token(raw_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()

    if stored is None or stored.revoked or as_aware_utc(stored.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    stored.revoked = True

    user_result = await db.execute(select(User).options(selectinload(User.roles)).where(User.id == stored.user_id))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account unavailable")

    new_raw, new_hash, new_expires = generate_refresh_token()
    db.add(RefreshToken(user_id=user.id, token_hash=new_hash, expires_at=new_expires))
    await db.commit()

    return user, new_raw, new_expires


async def revoke_refresh_token(db: AsyncSession, raw_token: str) -> None:
    token_hash = hash_refresh_token(raw_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    stored = result.scalar_one_or_none()
    if stored is not None:
        stored.revoked = True
        await db.commit()
