import base64
import json
import re
import secrets
from dataclasses import dataclass
from urllib.parse import quote, urlencode

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.brand import Brand
from app.models.enums import UserType, WalletOwnerType
from app.models.influencer import Influencer
from app.models.rbac import Role
from app.models.user import User
from app.services.audit import write_audit_log
from app.services.wallet import create_wallet_for_owner

settings = get_settings()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_LOGIN_SCOPES = "openid email profile"

SUPPORTED_PROVIDERS = {"google"}


@dataclass(frozen=True)
class OAuthUserInfo:
    subject: str
    email: str
    email_verified: bool
    name: str


def _require_supported(provider: str) -> None:
    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported provider '{provider}'")


def _google_is_configured() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def build_authorization_url(*, provider: str, state: str, redirect_uri: str) -> str:
    _require_supported(provider)

    if _google_is_configured():
        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": GOOGLE_LOGIN_SCOPES,
            "state": state,
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    # Mock mode: same idea as services/social/mock.py — send the browser to our
    # own frontend's mock consent page instead of a real (nonexistent) Google
    # app, so "Continue with Google" is clickable end-to-end without real
    # credentials. Unlike the social-connect mock, this one needs the tester to
    # actually type an email/name, since that becomes the account's identity.
    return (
        f"{settings.FRONTEND_BASE_URL}/oauth-login/mock-consent/{provider}"
        f"?state={quote(state)}&redirect_uri={quote(redirect_uri)}"
    )


async def exchange_code(*, provider: str, code: str, redirect_uri: str) -> OAuthUserInfo:
    _require_supported(provider)

    if _google_is_configured():
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri,
                },
            )
            token_resp.raise_for_status()
            access_token = token_resp.json()["access_token"]

            userinfo_resp = await client.get(
                GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
            )
            userinfo_resp.raise_for_status()
            body = userinfo_resp.json()

        return OAuthUserInfo(
            subject=body["sub"],
            email=body["email"].lower(),
            email_verified=bool(body.get("email_verified", False)),
            name=body.get("name") or body["email"],
        )

    # Mock mode: `code` is a base64url JSON blob the mock consent page built
    # from whatever email/name the tester typed in — see
    # frontend/src/app/oauth-login/mock-consent/[provider]/page.tsx.
    try:
        decoded = json.loads(base64.urlsafe_b64decode(code.encode()).decode())
        email = str(decoded["email"]).strip().lower()
        if not email:
            raise ValueError("empty email")
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid mock OAuth code")

    return OAuthUserInfo(
        subject=f"mock-{email}", email=email, email_verified=True, name=str(decoded.get("name") or email)
    )


async def _generate_unique_username(db: AsyncSession, base: str) -> str:
    slug = re.sub(r"[^a-z0-9_]", "", base.lower()) or "user"
    candidate = slug
    suffix = 0
    while True:
        result = await db.execute(select(Influencer.username).where(Influencer.username == candidate))
        if result.scalar_one_or_none() is None:
            return candidate
        suffix += 1
        candidate = f"{slug}{suffix}"


async def login_or_register_via_oauth(
    db: AsyncSession, *, provider: str, info: OAuthUserInfo, user_type: UserType | None
) -> tuple[User, bool]:
    """Returns (user, created). Three paths, in order: an account already
    linked to this exact (provider, subject); an existing password account
    with the same *provider-verified* email (auto-linked — Google only ever
    reports an address as verified once it controls delivery to it, so this
    is as trustworthy as the email-confirmation link CLOUT's own signup
    sends); or a brand-new account, which needs `user_type` since a brand and
    an influencer collect different required fields.
    """
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles))
        .where(User.oauth_provider == provider, User.oauth_subject == info.subject)
    )
    user = result.scalar_one_or_none()
    if user is not None:
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
        return user, False

    if info.email_verified:
        result = await db.execute(select(User).options(selectinload(User.roles)).where(User.email == info.email))
        existing = result.scalar_one_or_none()
        if existing is not None:
            if not existing.is_active:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
            existing.oauth_provider = provider
            existing.oauth_subject = info.subject
            existing.is_verified = True
            await db.commit()
            await db.refresh(existing, attribute_names=["roles"])
            return existing, False

    if user_type is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No CLOUT account is linked to this Google identity yet — register as a brand or influencer first.",
        )

    role_result = await db.execute(select(Role).where(Role.name == user_type.value))
    role = role_result.scalar_one()

    user = User(
        email=info.email,
        hashed_password=hash_password(secrets.token_urlsafe(32)),
        user_type=user_type,
        is_active=True,
        is_verified=info.email_verified,
        oauth_provider=provider,
        oauth_subject=info.subject,
    )
    user.roles.append(role)
    db.add(user)
    await db.flush()

    if user_type == UserType.BRAND:
        db.add(Brand(id=user.id, business_name=info.name, contact_email=info.email))
        await create_wallet_for_owner(db, owner_type=WalletOwnerType.BRAND, owner_id=user.id)
    else:
        username = await _generate_unique_username(db, info.email.split("@")[0])
        db.add(Influencer(id=user.id, display_name=info.name, username=username))
        await create_wallet_for_owner(db, owner_type=WalletOwnerType.INFLUENCER, owner_id=user.id)

    await write_audit_log(
        db,
        actor_user_id=user.id,
        action="user.register",
        entity_type="user",
        entity_id=user.id,
        after={"method": f"oauth:{provider}"},
    )
    await db.commit()

    result = await db.execute(select(User).options(selectinload(User.roles)).where(User.id == user.id))
    return result.scalar_one(), True
