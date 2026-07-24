"""School management routes (platform admins only)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.core.dependencies import DB, RequirePlatformAdmin, Pagination
from app.models.school import School
from app.schemas.school import SchoolCreate, SchoolOut, SchoolUpdate

router = APIRouter()


@router.get("", response_model=dict)
async def list_schools(
    db: DB,
    current_user: RequirePlatformAdmin,
    pagination: Pagination = Depends(),
    search: str = "",
):
    base = select(School)
    count_q = select(func.count(School.id))
    if search:
        ilike = f"%{search}%"
        base = base.where(School.name.ilike(ilike))
        count_q = count_q.where(School.name.ilike(ilike))

    total = await db.scalar(count_q)
    rows = (
        await db.scalars(
            base.order_by(School.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
    ).all()

    return {
        "items": [SchoolOut.model_validate(r) for r in rows],
        "total": total or 0,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.post("", response_model=SchoolOut, status_code=status.HTTP_201_CREATED)
async def create_school(
    payload: SchoolCreate, db: DB, current_user: RequirePlatformAdmin
):
    existing = await db.scalar(select(School).where(School.code == payload.code))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="School code already exists")
    school = School(**payload.model_dump())
    db.add(school)
    await db.flush()
    await db.refresh(school)
    return SchoolOut.model_validate(school)


@router.get("/{school_id}", response_model=SchoolOut)
async def get_school(
    school_id: uuid.UUID, db: DB, current_user: RequirePlatformAdmin
):
    school = await db.scalar(select(School).where(School.id == school_id))
    if not school:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return SchoolOut.model_validate(school)


@router.patch("/{school_id}", response_model=SchoolOut)
async def update_school(
    school_id: uuid.UUID,
    payload: SchoolUpdate,
    db: DB,
    current_user: RequirePlatformAdmin,
):
    school = await db.scalar(select(School).where(School.id == school_id))
    if not school:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(school, field, value)
    await db.flush()
    await db.refresh(school)
    return SchoolOut.model_validate(school)


@router.post("/{school_id}/toggle-active", response_model=SchoolOut)
async def toggle_school_active(
    school_id: uuid.UUID, db: DB, current_user: RequirePlatformAdmin
):
    school = await db.scalar(select(School).where(School.id == school_id))
    if not school:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    school.is_active = not school.is_active
    await db.flush()
    await db.refresh(school)
    return SchoolOut.model_validate(school)
