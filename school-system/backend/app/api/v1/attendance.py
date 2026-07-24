"""Attendance routes."""

from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.dependencies import CurrentUser, DB, RequireStaff, Pagination
from app.models.attendance import AttendanceRecord
from app.models.student import Student
from app.schemas.attendance import (
    AttendanceBatchCreate,
    AttendanceHistory,
    AttendanceOut,
    AttendanceStats,
)

router = APIRouter()


@router.post("/batch", status_code=status.HTTP_201_CREATED)
async def record_attendance(
    payload: AttendanceBatchCreate, db: DB, current_user: RequireStaff
):
    """Record attendance for a batch of students in one class."""
    try:
        return await _do_record_attendance(payload, db, current_user)
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to record attendance")


async def _do_record_attendance(
    payload: AttendanceBatchCreate, db: DB, current_user: RequireStaff
):
    # Verify all students belong to the school
    student_ids = [r.student_id for r in payload.records]
    valid_students = await db.scalars(
        select(Student.id).where(
            Student.id.in_(student_ids),
            Student.school_id == current_user.school_id,
        )
    )
    valid_set = set(valid_students.all())

    records = []
    for entry in payload.records:
        if entry.student_id not in valid_set:
            continue

        # Upsert: update if already recorded for the same date
        existing = await db.scalar(
            select(AttendanceRecord).where(
                AttendanceRecord.student_id == entry.student_id,
                AttendanceRecord.school_id == current_user.school_id,
                AttendanceRecord.attendance_date == payload.attendance_date,
            )
        )
        if existing:
            existing.status = entry.status
            existing.remarks = entry.remarks
            existing.recorded_by = current_user.id
            records.append(existing)
        else:
            records.append(
                AttendanceRecord(
                    school_id=current_user.school_id,
                    student_id=entry.student_id,
                    class_id=payload.class_id,
                    recorded_by=current_user.id,
                    attendance_date=payload.attendance_date,
                    status=entry.status,
                    remarks=entry.remarks,
                )
            )

    db.add_all(records)
    await db.flush()
    return {"recorded": len(records)}


@router.get("/class/{class_id}", response_model=AttendanceHistory)
async def get_class_attendance(
    class_id: uuid.UUID,
    db: DB,
    current_user: RequireStaff,
    attendance_date: date = Query(default_factory=date.today),
):
    """Get attendance for a class on a specific date with stats."""
    # Get all students in the class
    students = await db.scalars(
        select(Student).where(
            Student.class_id == class_id,
            Student.school_id == current_user.school_id,
            Student.status == "active",
        )
    )
    student_list = students.all()
    total = len(student_list)

    records = await db.scalars(
        select(AttendanceRecord).where(
            AttendanceRecord.class_id == class_id,
            AttendanceRecord.school_id == current_user.school_id,
            AttendanceRecord.attendance_date == attendance_date,
        )
    )
    record_list = records.all()

    present = sum(1 for r in record_list if r.status == "present")
    absent = sum(1 for r in record_list if r.status == "absent")
    late = sum(1 for r in record_list if r.status == "late")
    excused = sum(1 for r in record_list if r.status == "excused")

    return AttendanceHistory(
        records=[AttendanceOut.model_validate(r) for r in record_list],
        stats=AttendanceStats(
            total_students=total,
            present=present,
            absent=absent,
            late=late,
            excused=excused,
            percentage=round((present / total * 100) if total else 0, 1),
        ),
    )


@router.get("/student/{student_id}", response_model=list[AttendanceOut])
async def get_student_attendance(
    student_id: uuid.UUID,
    db: DB,
    current_user: RequireStaff,
    days: int = Query(30, le=365),
):
    """Get attendance history for a specific student."""
    from datetime import date as date_type, timedelta

    cutoff = date_type.today() - timedelta(days=days)
    records = await db.scalars(
        select(AttendanceRecord)
        .where(
            AttendanceRecord.student_id == student_id,
            AttendanceRecord.school_id == current_user.school_id,
            AttendanceRecord.attendance_date >= cutoff,
        )
        .order_by(AttendanceRecord.attendance_date.desc())
    )
    return [AttendanceOut.model_validate(r) for r in records]


@router.get("/stats", response_model=AttendanceStats)
async def attendance_stats(
    db: DB,
    current_user: RequireStaff,
    class_id: str = "",
    attendance_date: date = Query(default_factory=date.today),
):
    """Get aggregate attendance stats for a class or whole school."""
    base = select(AttendanceRecord).join(Student).where(
        Student.school_id == current_user.school_id,
        AttendanceRecord.attendance_date == attendance_date,
    )
    if class_id:
        base = base.where(AttendanceRecord.class_id == uuid.UUID(class_id))

    records = await db.scalars(base)
    record_list = records.all()

    total = len(record_list)
    present = sum(1 for r in record_list if r.status == "present")
    absent = sum(1 for r in record_list if r.status == "absent")
    late = sum(1 for r in record_list if r.status == "late")
    excused = sum(1 for r in record_list if r.status == "excused")

    return AttendanceStats(
        total_students=total,
        present=present,
        absent=absent,
        late=late,
        excused=excused,
        percentage=round((present / total * 100) if total else 0, 1),
    )
