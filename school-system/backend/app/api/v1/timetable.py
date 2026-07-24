"""Timetable routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.dependencies import DB, RequireSchoolAdmin, RequireStaff
from app.models.timetable import Timetable, TimetableEntry
from app.schemas.timetable import (
    ConflictCheck,
    TimetableCreate,
    TimetableEntryCreate,
    TimetableEntryOut,
    TimetableOut,
)

router = APIRouter()


@router.get("", response_model=list[TimetableOut])
async def list_timetables(db: DB, current_user: RequireStaff):
    rows = await db.scalars(
        select(Timetable)
        .where(Timetable.school_id == current_user.school_id)
        .options(selectinload(Timetable.entries))
        .order_by(Timetable.created_at.desc())
    )
    return [TimetableOut.model_validate(r) for r in rows]


@router.post("", response_model=TimetableOut, status_code=status.HTTP_201_CREATED)
async def create_timetable(
    payload: TimetableCreate, db: DB, current_user: RequireSchoolAdmin
):
    timetable = Timetable(
        school_id=current_user.school_id,
        academic_year_id=payload.academic_year_id,
        name=payload.name,
    )
    db.add(timetable)
    await db.flush()

    for entry in payload.entries:
        db.add(
            TimetableEntry(
                timetable_id=timetable.id, **entry.model_dump()
            )
        )
    await db.flush()
    await db.refresh(timetable)
    # reload with entries
    timetable = await db.scalar(
        select(Timetable)
        .where(Timetable.id == timetable.id)
        .options(selectinload(Timetable.entries))
    )
    return TimetableOut.model_validate(timetable)


@router.get("/{timetable_id}", response_model=TimetableOut)
async def get_timetable(
    timetable_id: uuid.UUID, db: DB, current_user: RequireStaff
):
    timetable = await db.scalar(
        select(Timetable)
        .where(
            Timetable.id == timetable_id,
            Timetable.school_id == current_user.school_id,
        )
        .options(selectinload(Timetable.entries))
    )
    if not timetable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return TimetableOut.model_validate(timetable)


@router.post("/{timetable_id}/entries", response_model=TimetableOut)
async def add_entry(
    timetable_id: uuid.UUID,
    payload: TimetableEntryCreate,
    db: DB,
    current_user: RequireSchoolAdmin,
):
    timetable = await db.scalar(
        select(Timetable).where(
            Timetable.id == timetable_id,
            Timetable.school_id == current_user.school_id,
        )
    )
    if not timetable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    # Conflict detection
    conflicts = await _detect_conflicts(db, timetable_id, payload)
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Scheduling conflict detected", "conflicts": conflicts},
        )

    entry = TimetableEntry(timetable_id=timetable.id, **payload.model_dump())
    db.add(entry)
    await db.flush()

    timetable = await db.scalar(
        select(Timetable)
        .where(Timetable.id == timetable_id)
        .options(selectinload(Timetable.entries))
    )
    return TimetableOut.model_validate(timetable)


@router.delete("/{timetable_id}/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_entry(
    timetable_id: uuid.UUID,
    entry_id: uuid.UUID,
    db: DB,
    current_user: RequireSchoolAdmin,
):
    entry = await db.scalar(
        select(TimetableEntry).where(
            TimetableEntry.id == entry_id,
            TimetableEntry.timetable_id == timetable_id,
            TimetableEntry.school_id == current_user.school_id,
        )
    )
    if entry:
        await db.delete(entry)
        await db.flush()


@router.get("/my", response_model=list[TimetableEntryOut])
async def my_timetable(db: DB, current_user: RequireStaff):
    """Return the timetable for the currently logged-in teacher."""
    from app.models.teacher import Teacher
    teacher = await db.scalar(
        select(Teacher).where(Teacher.user_id == current_user.id)
    )
    if not teacher:
        return []
    entries = await db.scalars(
        select(TimetableEntry)
        .join(Timetable)
        .where(
            Timetable.school_id == current_user.school_id,
            TimetableEntry.teacher_id == teacher.id,
            Timetable.is_active == True,
        )
        .order_by(TimetableEntry.day_of_week, TimetableEntry.start_time)
    )
    return [TimetableEntryOut.model_validate(e) for e in entries]


@router.post("/check-conflicts")
async def check_conflicts(
    payload: ConflictCheck, db: DB, current_user: RequireSchoolAdmin
):
    conflicts = await _detect_conflicts_raw(db, current_user.school_id, payload)
    return {"has_conflicts": len(conflicts) > 0, "conflicts": conflicts}


# ── Helpers ──────────────────────────────────────────────────────────


async def _detect_conflicts(
    db, timetable_id: uuid.UUID, entry: TimetableEntryCreate
) -> list[dict]:
    """Return list of conflicting entries within the same timetable."""
    result = await db.scalars(
        select(TimetableEntry).where(
            TimetableEntry.timetable_id == timetable_id,
            TimetableEntry.day_of_week == entry.day_of_week,
            TimetableEntry.start_time < entry.end_time,
            TimetableEntry.end_time > entry.start_time,
            (
                (TimetableEntry.teacher_id == entry.teacher_id)
                | (TimetableEntry.class_id == entry.class_id)
                | (
                    TimetableEntry.room == entry.room
                    if entry.room
                    else False
                )
            ),
        )
    )
    conflicts = result.all()
    return [
        {
            "id": str(c.id),
            "day": c.day_of_week,
            "start": str(c.start_time),
            "end": str(c.end_time),
            "reason": (
                "teacher" if c.teacher_id == entry.teacher_id
                else "class" if c.class_id == entry.class_id
                else "room"
            ),
        }
        for c in conflicts
    ]


async def _detect_conflicts_raw(db, school_id, payload: ConflictCheck) -> list[dict]:
    """Check conflicts across all active timetables in a school."""
    result = await db.scalars(
        select(TimetableEntry)
        .join(Timetable)
        .where(
            Timetable.school_id == school_id,
            Timetable.is_active == True,
            TimetableEntry.day_of_week == payload.day_of_week,
            TimetableEntry.start_time < payload.end_time,
            TimetableEntry.end_time > payload.start_time,
        )
    )
    conflicts = []
    for c in result:
        reasons = []
        if payload.teacher_id and c.teacher_id == payload.teacher_id:
            reasons.append("teacher")
        if payload.class_id and c.class_id == payload.class_id:
            reasons.append("class")
        if payload.room and c.room == payload.room:
            reasons.append("room")
        if reasons:
            conflicts.append({"id": str(c.id), "reasons": reasons})
    return conflicts
