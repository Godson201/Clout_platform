import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings

settings = get_settings()
_hasher = PasswordHasher()


def hash_password(raw_password: str) -> str:
    return _hasher.hash(raw_password)


def verify_password(raw_password: str, hashed_password: str) -> bool:
    try:
        return _hasher.verify(hashed_password, raw_password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def create_access_token(*, user_id: uuid.UUID, user_type: str, roles: list[str]) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "user_type": user_type,
        "roles": roles,
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Not an access token")
    return payload


def _sha256_hex(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def generate_refresh_token() -> tuple[str, str, datetime]:
    """Returns (raw_token_for_client, sha256_hash_for_storage, expires_at)."""
    raw = secrets.token_urlsafe(64)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return raw, _sha256_hex(raw), expires_at


def hash_refresh_token(raw_token: str) -> str:
    return _sha256_hex(raw_token)


def generate_secure_token(expire_minutes: int) -> tuple[str, str, datetime]:
    """Same shape as generate_refresh_token, for the shorter-lived, single-use
    tokens behind email verification and password reset links."""
    raw = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    return raw, _sha256_hex(raw), expires_at


def hash_secure_token(raw_token: str) -> str:
    return _sha256_hex(raw_token)


def as_aware_utc(value: datetime) -> datetime:
    """SQLite (used in tests) drops tzinfo on round-trip even for DateTime(timezone=True)
    columns; Postgres (production) preserves it. Normalize before comparing so the same
    code path is correct on both.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
