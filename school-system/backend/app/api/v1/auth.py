"""Auth routes — multi-tenant login, first-login, password management."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from app.core.dependencies import CurrentUser, DB
from app.schemas.auth import (
    ChangePasswordRequest,
    FirstLoginRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from app.services import auth_service

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request, db: DB):
    """Multi-tenant authentication: school_code + username + password."""
    ip = request.client.host if request.client else ""
    ua = request.headers.get("user-agent", "")
    return await auth_service.authenticate(db, payload, ip, ua)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: DB):
    """Rotate refresh token and issue new pair."""
    return await auth_service.refresh_access_token(db, payload.refresh_token)


@router.post("/first-login", response_model=TokenResponse)
async def first_login(
    payload: FirstLoginRequest,
    current_user: CurrentUser,
    request: Request,
    db: DB,
):
    """Complete the first-login flow: set password, confirm email, accept terms."""
    ip = request.client.host if request.client else ""
    result = await auth_service.complete_first_login(
        db, current_user,
        new_password=payload.new_password,
        email=str(payload.email) if payload.email else None,
        phone=payload.phone,
        accept_terms=payload.accept_terms,
        ip=ip,
    )
    return result


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: CurrentUser,
    db: DB,
):
    """Change the current user's password."""
    await auth_service.change_password(
        db, current_user, payload.current_password, payload.new_password
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(current_user: CurrentUser, db: DB):
    """Revoke all refresh tokens for the current user."""
    current_user.refresh_token_jti = None
    await db.flush()


@router.get("/me")
async def me(current_user: CurrentUser):
    """Return the currently authenticated user's profile."""
    from app.schemas.user import UserOut
    return UserOut.model_validate(current_user)
