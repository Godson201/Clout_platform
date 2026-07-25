import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.crypto import encrypt_token
from app.core.security import as_aware_utc
from app.models.enums import SocialAccountStatus, SocialPlatform
from app.models.social_account import SocialAccount
from app.models.social_oauth_state import SocialOAuthState
from app.models.user import User
from app.services.audit import write_audit_log
from app.services.social import get_adapter

settings = get_settings()

STATE_TTL_MINUTES = 10


async def initiate_connection(db: AsyncSession, *, user: User, platform: SocialPlatform) -> str:
    adapter = get_adapter(platform)
    state = secrets.token_urlsafe(32)
    redirect_uri = f"{settings.FRONTEND_BASE_URL}/social/callback/{platform.value}"

    auth_request = adapter.build_authorization_url(state=state, redirect_uri=redirect_uri)

    db.add(
        SocialOAuthState(
            user_id=user.id,
            platform=platform,
            state=state,
            code_verifier=auth_request.code_verifier,
            redirect_uri=redirect_uri,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=STATE_TTL_MINUTES),
        )
    )
    await db.commit()
    return auth_request.authorization_url


async def complete_connection(
    db: AsyncSession, *, user: User, platform: SocialPlatform, code: str, state: str
) -> SocialAccount:
    result = await db.execute(select(SocialOAuthState).where(SocialOAuthState.state == state))
    pending = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if (
        pending is None
        or pending.consumed
        or pending.user_id != user.id
        or pending.platform != platform
        or as_aware_utc(pending.expires_at) < now
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OAuth state")

    # Marked consumed before the token exchange (and committed win-or-lose via
    # the caller's request lifecycle) so a retried/duplicated callback with the
    # same state can't replay the exchange.
    pending.consumed = True

    adapter = get_adapter(platform)
    token_result = await adapter.exchange_code_for_token(
        code=code, redirect_uri=pending.redirect_uri, code_verifier=pending.code_verifier
    )

    existing = await db.execute(
        select(SocialAccount).where(SocialAccount.owner_user_id == user.id, SocialAccount.platform == platform)
    )
    account = existing.scalar_one_or_none()

    expires_at = None
    if token_result.expires_in_seconds is not None:
        expires_at = now + timedelta(seconds=token_result.expires_in_seconds)

    if account is None:
        account = SocialAccount(
            owner_user_id=user.id,
            platform=platform,
            external_account_id=token_result.external_account_id,
            handle=token_result.handle,
            access_token_encrypted=encrypt_token(token_result.access_token),
            refresh_token_encrypted=(
                encrypt_token(token_result.refresh_token) if token_result.refresh_token else None
            ),
            token_expires_at=expires_at,
            scopes=token_result.scopes,
            status=SocialAccountStatus.ACTIVE,
        )
        db.add(account)
    else:
        account.external_account_id = token_result.external_account_id
        account.handle = token_result.handle
        account.access_token_encrypted = encrypt_token(token_result.access_token)
        account.refresh_token_encrypted = (
            encrypt_token(token_result.refresh_token) if token_result.refresh_token else None
        )
        account.token_expires_at = expires_at
        account.scopes = token_result.scopes
        account.status = SocialAccountStatus.ACTIVE

    await db.flush()  # populates account.id for the audit log below on first connect

    await write_audit_log(
        db,
        actor_user_id=user.id,
        action="social_account.connect",
        entity_type="social_account",
        entity_id=account.id,
        after={"platform": platform.value, "handle": token_result.handle},
    )

    await db.commit()
    await db.refresh(account)
    return account


async def disconnect_account(db: AsyncSession, *, user: User, account: SocialAccount) -> None:
    account.status = SocialAccountStatus.DISCONNECTED
    await write_audit_log(
        db,
        actor_user_id=user.id,
        action="social_account.disconnect",
        entity_type="social_account",
        entity_id=account.id,
    )
    await db.commit()
