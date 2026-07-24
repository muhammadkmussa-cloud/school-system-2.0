"""School Management System — Authentication service.

Multi-tenant login flow:
  1. Look up school by code
  2. Authenticate user by username within that school's tenant
  3. Enforce account lifecycle (pending, locked, disabled)
  4. Track failed attempts with lockout
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import LoginHistory, User
from app.models.school import School
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.user import UserOut
from app.services.audit_service import log_account_event


async def authenticate(
    db: AsyncSession, payload: LoginRequest, ip: str = "", ua: str = ""
) -> TokenResponse:
    """Authentication: username/email + password (school_code is optional/deprecated)."""
    school_code = (payload.school_code or "").strip()
    username = (payload.username or "").strip()

    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email is required",
        )

    # Step 1: Find user by email or username
    user = await db.scalar(
        select(User).where(
            (User.email == username) | (User.username == username)
        )
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Step 2: Look up and verify school
    school = await db.get(School, user.school_id)
    if not school or not school.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Step 3: If school_code is provided, verify it matches
    if school_code and school.code.strip() != school_code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid school code",
        )

    # --- Account lifecycle enforcement ---

    # Disabled accounts cannot login
    if user.status == "disabled" or not user.is_active:
        await _log_login(db, user, ip, ua, False)
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is disabled. Contact your school administrator.",
        )

    # Check lockout
    if user.status == "locked" or (user.locked_until and user.locked_until > datetime.now(timezone.utc)):
        await _log_login(db, user, ip, ua, False)
        remaining = user.locked_until - datetime.now(timezone.utc) if user.locked_until else timedelta(minutes=15)
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account temporarily locked. Try again in {int(remaining.total_seconds() // 60)} minutes.",
        )

    # Step 3: Verify password
    if not verify_password(payload.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.FAILED_LOGIN_LOCKOUT:
            user.status = "locked"
            user.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=settings.FAILED_LOGIN_WINDOW_MINUTES
            )
            await log_account_event(
                db, school.id, None, user.role, user.full_name,
                "account_locked", str(user.id), user.email,
                changes={"failed_login_attempts": user.failed_login_attempts},
                ip_address=ip, endpoint="/auth/login",
            )
        await db.flush()
        await _log_login(db, user, ip, ua, False)
        await log_account_event(
            db, school.id, None, user.role, user.full_name,
            "failed_login", str(user.id), user.email,
            changes={"attempt": user.failed_login_attempts},
            ip_address=ip, endpoint="/auth/login",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid school code or credentials",
        )

    # Success — reset counters
    user.failed_login_attempts = 0
    user.locked_until = None
    if user.status == "locked":
        user.status = "active"
    user.last_login_at = datetime.now(timezone.utc)

    # Generate tokens
    jti = uuid.uuid4().hex
    access_token = create_access_token(
        str(user.id),
        extra={
            "role": user.role,
            "school_id": str(user.school_id),
            "status": user.status,
            "must_change_password": str(user.must_change_password).lower(),
        },
    )
    refresh_token = create_refresh_token(str(user.id), jti)
    user.refresh_token_jti = jti

    await db.flush()
    await _log_login(db, user, ip, ua, True)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
        must_change_password=user.must_change_password,
        account_status=user.status,
    )


async def refresh_access_token(db: AsyncSession, token_str: str) -> TokenResponse:
    """Rotate refresh token and issue new access + refresh pair."""
    try:
        payload = decode_token(token_str)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user_id = uuid.UUID(payload["sub"])
    jti = payload.get("jti")

    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None or not user.is_active or user.status == "disabled":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    if settings.REFRESH_TOKEN_ROTATION and user.refresh_token_jti != jti:
        user.refresh_token_jti = None
        await db.flush()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    new_jti = uuid.uuid4().hex
    access_token = create_access_token(
        str(user.id),
        extra={"role": user.role, "school_id": str(user.school_id)},
    )
    refresh_token = create_refresh_token(str(user.id), new_jti)
    user.refresh_token_jti = new_jti
    await db.flush()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
        must_change_password=user.must_change_password,
        account_status=user.status,
    )


async def change_password(
    db: AsyncSession, user: User, current_pw: str, new_pw: str
) -> None:
    if current_pw and not verify_password(current_pw, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Store old password in history (keep last 5)
    from app.models.user import PasswordHistory
    old_entry = PasswordHistory(
        user_id=user.id,
        hashed_password=user.hashed_password,
    )
    db.add(old_entry)

    # Check password reuse (last 5)
    recent = await db.scalars(
        select(PasswordHistory).where(PasswordHistory.user_id == user.id)
        .order_by(PasswordHistory.created_at.desc())
        .limit(5)
    )
    for entry in recent:
        if verify_password(new_pw, entry.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have used this password recently. Choose a different one.",
            )

    user.hashed_password = hash_password(new_pw)
    user.must_change_password = False
    user.password_changed_at = datetime.now(timezone.utc)
    user.refresh_token_jti = None
    await db.flush()


async def complete_first_login(
    db: AsyncSession,
    user: User,
    new_password: str,
    email: str | None = None,
    phone: str | None = None,
    accept_terms: bool = False,
    ip: str = "",
) -> None:
    """Complete the first-login flow: set password, confirm email, accept terms."""
    if new_password:
        # Store old password in history before changing
        from app.models.user import PasswordHistory
        db.add(PasswordHistory(user_id=user.id, hashed_password=user.hashed_password))
        user.hashed_password = hash_password(new_password)

    if email:
        # Check email uniqueness
        existing = await db.scalar(
            select(User).where(User.email == email, User.id != user.id)
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use by another account",
            )
        user.email = email
        user.is_verified = True

    if phone:
        user.phone = phone

    if accept_terms:
        user.terms_accepted = True

    user.must_change_password = False
    user.profile_completed = True
    user.status = "active"
    user.password_changed_at = datetime.now(timezone.utc)
    user.refresh_token_jti = None
    user.last_login_at = datetime.now(timezone.utc)

    await db.flush()

    # Audit
    from app.models.school import School
    school = await db.scalar(select(School).where(School.id == user.school_id))
    await log_account_event(
        db, user.school_id, user.id, user.role, user.full_name,
        "first_login_completed", str(user.id), user.email,
        changes={"status": "active"},
        ip_address=ip, endpoint="/auth/first-login",
    )

    # Issue new tokens
    jti = uuid.uuid4().hex
    access_token = create_access_token(
        str(user.id),
        extra={"role": user.role, "school_id": str(user.school_id), "status": "active"},
    )
    refresh_token = create_refresh_token(str(user.id), jti)
    user.refresh_token_jti = jti

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserOut.model_validate(user),
        must_change_password=False,
        account_status="active",
    )


async def _log_login(
    db: AsyncSession, user: User, ip: str, ua: str, success: bool
) -> None:
    db.add(
        LoginHistory(
            user_id=user.id,
            ip_address=ip,
            user_agent=ua,
            success=success,
        )
    )
