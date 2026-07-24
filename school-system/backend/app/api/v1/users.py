"""User management routes (school admins manage their teachers)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.core.config import settings
from app.core.dependencies import CurrentUser, DB, RequireSchoolAdmin, Pagination
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserCreate, UserList, UserOut, UserUpdate

router = APIRouter()


@router.get("", response_model=UserList)
async def list_users(
    db: DB,
    current_user: RequireSchoolAdmin,
    pagination: Pagination = Depends(),
    search: str = "",
    role: str = "",
):
    """List users within the admin's school."""
    base = select(User).where(User.school_id == current_user.school_id)
    count_q = select(func.count(User.id)).where(
        User.school_id == current_user.school_id
    )

    if search:
        ilike = f"%{search}%"
        base = base.where(
            (User.full_name.ilike(ilike)) | (User.email.ilike(ilike))
        )
        count_q = count_q.where(
            (User.full_name.ilike(ilike)) | (User.email.ilike(ilike))
        )
    if role:
        base = base.where(User.role == role)
        count_q = count_q.where(User.role == role)

    total = await db.scalar(count_q)
    rows = (
        await db.scalars(
            base.order_by(User.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
    ).all()

    return UserList(
        items=[UserOut.model_validate(r) for r in rows],
        total=total or 0,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, db: DB, current_user: RequireSchoolAdmin):
    """Create a new user (teacher or school_admin) in the admin's school."""
    # Check limits
    count = await db.scalar(
        select(func.count(User.id)).where(
            User.school_id == current_user.school_id
        )
    )
    if count and count >= settings.MAX_TEACHERS_PER_SCHOOL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum teachers reached for this school",
        )

    # Check duplicate email
    existing = await db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    password = payload.password or uuid.uuid4().hex[:12]
    user = User(
        school_id=current_user.school_id,
        email=payload.email,
        hashed_password=hash_password(password),
        full_name=payload.full_name,
        role=payload.role,
        phone=payload.phone,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: uuid.UUID, db: DB, current_user: RequireSchoolAdmin):
    user = await db.scalar(
        select(User).where(
            User.id == user_id, User.school_id == current_user.school_id
        )
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return UserOut.model_validate(user)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: DB,
    current_user: RequireSchoolAdmin,
):
    user = await db.scalar(
        select(User).where(
            User.id == user_id, User.school_id == current_user.school_id
        )
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.flush()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/{user_id}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(
    user_id: uuid.UUID, db: DB, current_user: RequireSchoolAdmin
):
    user = await db.scalar(
        select(User).where(
            User.id == user_id, User.school_id == current_user.school_id
        )
    )
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    new_pw = uuid.uuid4().hex[:12]
    user.hashed_password = hash_password(new_pw)
    user.refresh_token_jti = None
    await db.flush()
    # In production, email this to the user
