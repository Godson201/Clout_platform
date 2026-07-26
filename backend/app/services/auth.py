import logging
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security import (
    as_aware_utc,
    create_access_token,
    generate_refresh_token,
    generate_secure_token,
    hash_password,
    hash_refresh_token,
    hash_secure_token,
    verify_password,
)
from app.models.brand import Brand
from app.models.email_token import EmailToken
from app.models.enums import EmailTokenPurpose, UserType, WalletOwnerType
from app.models.influencer import Influencer
from app.models.rbac import Role
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import BrandRegisterRequest, InfluencerRegisterRequest
from app.services.audit import write_audit_log
from app.services.email import get_email_sender
from app.services.email.templates import password_changed_email, password_reset_email, verification_email
from app.services.wallet import create_wallet_for_owner

settings = get_settings()
logger = logging.getLogger("clout.auth")


def _normalize_answer(raw: str) -> str:
    return raw.strip().lower()


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
        security_question=payload.security_question,
        security_answer_hash=hash_password(_normalize_answer(payload.security_answer))
        if payload.security_answer
        else None,
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
        province=payload.province,
        location=payload.location,
        admin_sector=payload.admin_sector,
        admin_cell=payload.admin_cell,
        admin_village=payload.admin_village,
        address_detail=payload.address_detail,
        contact_email=payload.email.lower(),
        contact_phone=payload.phone_number,
    )
    db.add(brand)

    await create_wallet_for_owner(db, owner_type=WalletOwnerType.BRAND, owner_id=user.id)
    await write_audit_log(db, actor_user_id=user.id, action="user.register", entity_type="user", entity_id=user.id)

    await db.commit()

    result = await db.execute(select(User).options(selectinload(User.roles)).where(User.id == user.id))
    registered = result.scalar_one()
    await _create_and_send_verification_email(db, registered)
    return registered


async def register_influencer(db: AsyncSession, payload: InfluencerRegisterRequest) -> User:
    role = await _get_role(db, "influencer")

    user = User(
        email=payload.email.lower(),
        phone_number=payload.phone_number,
        hashed_password=hash_password(payload.password),
        user_type=UserType.INFLUENCER,
        security_question=payload.security_question,
        security_answer_hash=hash_password(_normalize_answer(payload.security_answer))
        if payload.security_answer
        else None,
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
        province=payload.province,
        location=payload.location,
        admin_sector=payload.admin_sector,
        admin_cell=payload.admin_cell,
        admin_village=payload.admin_village,
        address_detail=payload.address_detail,
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
    registered = result.scalar_one()
    await _create_and_send_verification_email(db, registered)
    return registered


async def _display_name(db: AsyncSession, user: User) -> str:
    # Fetched via a fresh primary-key lookup rather than user.brand/user.influencer
    # — those relationships aren't eager-loaded on every User this is called with
    # (e.g. from get_current_user), and touching them here would trigger an
    # implicit lazy-load that fails under AsyncSession (MissingGreenlet).
    if user.user_type == UserType.BRAND:
        brand = await db.get(Brand, user.id)
        if brand is not None:
            return brand.business_name
    elif user.user_type == UserType.INFLUENCER:
        influencer = await db.get(Influencer, user.id)
        if influencer is not None:
            return influencer.display_name
    return user.email


async def _create_and_send_verification_email(db: AsyncSession, user: User) -> None:
    raw, token_hash, expires_at = generate_secure_token(settings.EMAIL_VERIFICATION_EXPIRE_MINUTES)
    db.add(EmailToken(user_id=user.id, purpose=EmailTokenPurpose.VERIFY_EMAIL, token_hash=token_hash, expires_at=expires_at))
    await db.commit()

    subject, html, text = verification_email(to_name=await _display_name(db, user), token=raw)
    try:
        await get_email_sender().send(to=user.email, subject=subject, html_body=html, text_body=text)
    except Exception:
        # Email delivery is best-effort — a flaky SMTP connection must never
        # block or roll back account creation. The user can request a resend.
        logger.exception("Failed to send verification email to %s", user.email)


async def resend_verification_email(db: AsyncSession, user: User) -> None:
    if user.is_verified:
        return
    await _create_and_send_verification_email(db, user)


async def verify_email(db: AsyncSession, raw_token: str) -> None:
    token = await _get_valid_token(db, raw_token, EmailTokenPurpose.VERIFY_EMAIL)
    user = await db.get(User, token.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    user.is_verified = True
    token.used_at = datetime.now(timezone.utc)
    await db.commit()


async def _get_valid_token(db: AsyncSession, raw_token: str, purpose: EmailTokenPurpose) -> EmailToken:
    token_hash = hash_secure_token(raw_token)
    result = await db.execute(
        select(EmailToken).where(EmailToken.token_hash == token_hash, EmailToken.purpose == purpose)
    )
    token = result.scalar_one_or_none()
    if token is None or token.used_at is not None or as_aware_utc(token.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    return token


async def request_password_reset(db: AsyncSession, email: str) -> None:
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        # Never reveal whether an email is registered — the endpoint always
        # returns success regardless of what happens here.
        return

    raw, token_hash, expires_at = generate_secure_token(settings.PASSWORD_RESET_EXPIRE_MINUTES)
    db.add(EmailToken(user_id=user.id, purpose=EmailTokenPurpose.RESET_PASSWORD, token_hash=token_hash, expires_at=expires_at))
    await db.commit()

    subject, html, text = password_reset_email(to_name=await _display_name(db, user), token=raw)
    try:
        await get_email_sender().send(to=user.email, subject=subject, html_body=html, text_body=text)
    except Exception:
        logger.exception("Failed to send password reset email to %s", user.email)


async def get_password_reset_prompt(db: AsyncSession, raw_token: str) -> str | None:
    """Returns the account's security question (if any) so the reset-password
    page can ask for it — the emailed link alone proves inbox access, this adds
    a second factor the user must also know."""
    token = await _get_valid_token(db, raw_token, EmailTokenPurpose.RESET_PASSWORD)
    user = await db.get(User, token.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")
    return user.security_question


async def reset_password(db: AsyncSession, *, raw_token: str, new_password: str, security_answer: str | None) -> None:
    token = await _get_valid_token(db, raw_token, EmailTokenPurpose.RESET_PASSWORD)
    user = await db.get(User, token.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    if user.security_question and user.security_answer_hash:
        if not security_answer or not verify_password(_normalize_answer(security_answer), user.security_answer_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Security answer did not match")

    user.hashed_password = hash_password(new_password)
    token.used_at = datetime.now(timezone.utc)

    # A password reset ends every other active session, not just the one that
    # requested it — otherwise a stolen-but-still-logged-in session survives
    # the very reset meant to lock it out.
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False))
        .values(revoked=True)
    )

    await write_audit_log(
        db, actor_user_id=user.id, action="user.password_reset", entity_type="user", entity_id=user.id
    )
    await db.commit()

    subject, html, text = password_changed_email(to_name=await _display_name(db, user))
    try:
        await get_email_sender().send(to=user.email, subject=subject, html_body=html, text_body=text)
    except Exception:
        logger.exception("Failed to send password-changed confirmation to %s", user.email)


async def change_password(db: AsyncSession, *, user: User, current_password: str, new_password: str) -> None:
    """Logged-in-user password change — distinct from reset_password (which
    proves identity via an emailed token instead of a known current password),
    but shares the same "log out every other session + confirmation email"
    behavior since both end with the account's credential changing.
    """
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    user.hashed_password = hash_password(new_password)

    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False))
        .values(revoked=True)
    )

    await write_audit_log(
        db, actor_user_id=user.id, action="user.password_change", entity_type="user", entity_id=user.id
    )
    await db.commit()

    subject, html, text = password_changed_email(to_name=await _display_name(db, user))
    try:
        await get_email_sender().send(to=user.email, subject=subject, html_body=html, text_body=text)
    except Exception:
        logger.exception("Failed to send password-changed confirmation to %s", user.email)


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
