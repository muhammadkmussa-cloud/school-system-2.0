"""School Management System — Security & Cryptography.

Implements the dual-token JWT scheme (short-lived access + revocable refresh)
and Argon2id password hashing.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# ── Argon2id hasher ──────────────────────────────────────────────────
_pwd_ctx = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__time_cost=settings.ARGON2_TIME_COST,
    argon2__memory_cost=settings.ARGON2_MEMORY_COST,
    argon2__parallelism=settings.ARGON2_PARALLELISM,
    argon2__hash_len=settings.ARGON2_HASH_LEN,
    argon2__salt_len=settings.ARGON2_SALT_LEN,
)


def hash_password(plain: str) -> str:
    """Return an Argon2id hash of *plain*."""
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return _pwd_ctx.verify(plain, hashed)


# ── JWT ──────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    """Return a short-lived access token for *subject* (user_id as str)."""
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": _now(),
        "exp": _now() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str, jti: str) -> str:
    """Return a long-lived refresh token with a unique *jti* for revocation."""
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": _now(),
        "exp": _now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        "type": "refresh",
        "jti": jti,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """Decode & verify *token*.  Raises JWTError on failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
