"""School Management System — FastAPI dependencies for auth, roles, and pagination."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False
)

DB = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: DB,
) -> User:
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user = await db.scalar(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str):
    """Factory: returns a dependency that only passes if user.role is in *roles."""

    async def _check(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _check


RequirePlatformAdmin = Annotated[User, Depends(require_role("platform_admin"))]
RequireSchoolAdmin = Annotated[
    User, Depends(require_role("platform_admin", "school_admin"))
]
RequireTeacher = Annotated[User, Depends(require_role("teacher"))]
RequireStaff = Annotated[
    User, Depends(require_role("platform_admin", "school_admin", "teacher"))
]


class Pagination:
    """Extract page/page_size from query params."""

    def __init__(
        self,
        page: int = Query(1, ge=1),
        page_size: int = Query(20, ge=1, le=200, alias="page_size"),
    ):
        self.page = page
        self.page_size = page_size
        self.offset = (page - 1) * page_size
