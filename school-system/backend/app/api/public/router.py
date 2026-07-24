"""School Management System — Public REST API.

A documented, versioned API for schools to integrate with:
- Finance / accounting systems
- LMS platforms
- Biometric attendance devices
- Third-party analytics tools

Authentication: API Key in X-API-Key header.
Rate limit: 1000 requests/minute per school.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select, func

from app.core.dependencies import DB, Pagination
from app.models.school import School
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.attendance import AttendanceRecord
from app.models.assessment import Assessment, Mark

router = APIRouter(prefix="/public/v1", tags=["Public API"])

# ── API Key auth ────────────────────────────────────────────────────

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

# In production: store hashed API keys in the schools table
# For now: validate against school code + secret
VALID_API_KEYS: dict[str, uuid.UUID] = {
    "demo-key-mombasa": uuid.UUID("00000000-0000-0000-0000-000000000001"),
}


async def get_school_from_api_key(
    api_key: str = Security(api_key_header),
    db: DB = None,
) -> School:
    """Validate API key and return the associated school."""
    school_id = VALID_API_KEYS.get(api_key)
    if not school_id:
        # Try lookup by school code (production: validate hashed key)
        school = await db.scalar(
            select(School).where(School.code == api_key, School.is_active == True)
        )
        if not school:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
        return school

    school = await db.scalar(select(School).where(School.id == school_id))
    if not school or not school.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return school


# ── Students ─────────────────────────────────────────────────────────


@router.get("/students")
async def list_students_public(
    request: Request,
    db: DB,
    school: School = Depends(get_school_from_api_key),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    class_id: str = "",
    search: str = "",
    updated_since: str = "",
):
    """List students. Supports incremental sync via updated_since."""
    base = select(Student).where(
        Student.school_id == school.id, Student.status == "active"
    )

    if class_id:
        base = base.where(Student.class_id == uuid.UUID(class_id))
    if search:
        ilike = f"%{search}%"
        base = base.where(Student.full_name.ilike(ilike))
    if updated_since:
        since_dt = datetime.fromisoformat(updated_since)
        base = base.where(Student.updated_at >= since_dt)

    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    offset = (page - 1) * page_size
    rows = (await db.scalars(base.order_by(Student.full_name).offset(offset).limit(page_size))).all()

    return {
        "students": [
            {
                "id": str(s.id),
                "admission_number": s.admission_number,
                "full_name": s.full_name,
                "gender": s.gender,
                "date_of_birth": str(s.date_of_birth),
                "class_id": str(s.class_id),
                "stream_id": str(s.stream_id) if s.stream_id else None,
                "status": s.status,
                "updated_at": s.updated_at.isoformat(),
            }
            for s in rows
        ],
        "total": total or 0,
        "page": page,
        "page_size": page_size,
    }


@router.get("/students/{student_id}")
async def get_student_public(
    student_id: uuid.UUID,
    db: DB,
    school: School = Depends(get_school_from_api_key),
):
    student = await db.scalar(
        select(Student).where(Student.id == student_id, Student.school_id == school.id)
    )
    if not student:
        raise HTTPException(status_code=404)
    return {
        "id": str(student.id),
        "admission_number": student.admission_number,
        "full_name": student.full_name,
        "gender": student.gender,
        "date_of_birth": str(student.date_of_birth),
        "class_id": str(student.class_id),
        "stream_id": str(student.stream_id) if student.stream_id else None,
        "status": student.status,
    }


# ── Attendance ─────────────────────────────────────────────────────


@router.get("/attendance")
async def get_attendance_public(
    db: DB,
    school: School = Depends(get_school_from_api_key),
    date_from: str = Query(default=""),
    date_to: str = Query(default=""),
    class_id: str = "",
    page: int = Query(1),
    page_size: int = Query(100, le=500),
):
    """Get attendance records. Perfect for biometric system integration."""
    base = (
        select(AttendanceRecord)
        .join(Student)
        .where(Student.school_id == school.id)
    )

    if date_from:
        base = base.where(AttendanceRecord.attendance_date >= date.fromisoformat(date_from))
    if date_to:
        base = base.where(AttendanceRecord.attendance_date <= date.fromisoformat(date_to))
    if class_id:
        base = base.where(AttendanceRecord.class_id == uuid.UUID(class_id))

    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    offset = (page - 1) * page_size
    rows = (await db.scalars(
        base.order_by(AttendanceRecord.attendance_date.desc()).offset(offset).limit(page_size)
    )).all()

    return {
        "records": [
            {
                "id": str(r.id),
                "student_id": str(r.student_id),
                "class_id": str(r.class_id),
                "attendance_date": str(r.attendance_date),
                "status": r.status,
                "remarks": r.remarks,
                "synced": r.synced,
                "updated_at": r.updated_at.isoformat(),
            }
            for r in rows
        ],
        "total": total or 0,
    }


# ── Marks / Grades ────────────────────────────────────────────────


@router.get("/marks")
async def get_marks_public(
    db: DB,
    school: School = Depends(get_school_from_api_key),
    assessment_id: str = "",
    student_id: str = "",
    page: int = Query(1),
    page_size: int = Query(100, le=500),
):
    """Get marks. Integrations can pull grades into LMS or analytics."""
    base = select(Mark).join(Assessment).where(Assessment.school_id == school.id)

    if assessment_id:
        base = base.where(Mark.assessment_id == uuid.UUID(assessment_id))
    if student_id:
        base = base.where(Mark.student_id == uuid.UUID(student_id))

    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    offset = (page - 1) * page_size
    rows = (await db.scalars(base.offset(offset).limit(page_size))).all()

    return {
        "marks": [
            {
                "id": str(m.id),
                "assessment_id": str(m.assessment_id),
                "student_id": str(m.student_id),
                "score": m.score,
                "grade": m.grade,
                "remarks": m.remarks,
                "updated_at": m.updated_at.isoformat(),
            }
            for m in rows
        ],
        "total": total or 0,
    }


# ── Teachers ──────────────────────────────────────────────────────


@router.get("/teachers")
async def list_teachers_public(
    db: DB,
    school: School = Depends(get_school_from_api_key),
):
    teachers = await db.scalars(
        select(Teacher).where(Teacher.school_id == school.id, Teacher.is_active == True)
    )
    return {
        "teachers": [
            {
                "id": str(t.id),
                "employee_number": t.employee_number,
                "full_name": t.full_name,
                "email": t.email,
                "phone": t.phone,
            }
            for t in teachers
        ]
    }


# ── Webhooks ──────────────────────────────────────────────────────

@router.post("/webhooks/attendance")
async def receive_attendance_webhook(
    payload: list[dict],
    db: DB,
    school: School = Depends(get_school_from_api_key),
):
    """Receive attendance records from biometric devices.

    Payload: [{"student_admission": "MSS/001", "date": "2026-07-12",
               "time": "08:15", "status": "present"}]
    """
    imported = 0
    for entry in payload:
        adm = entry.get("student_admission")
        att_date = entry.get("date")

        student = await db.scalar(
            select(Student).where(
                Student.school_id == school.id,
                Student.admission_number == adm,
            )
        )
        if not student:
            continue

        # Upsert attendance
        existing = await db.scalar(
            select(AttendanceRecord).where(
                AttendanceRecord.student_id == student.id,
                AttendanceRecord.attendance_date == att_date,
            )
        )
        if existing:
            existing.status = entry.get("status", "present")
        else:
            db.add(AttendanceRecord(
                student_id=student.id,
                class_id=student.class_id,
                recorded_by=uuid.UUID("00000000-0000-0000-0000-000000000000"),  # system
                attendance_date=att_date,
                status=entry.get("status", "present"),
                synced=False,
            ))
        imported += 1

    await db.flush()
    return {"imported": imported}


# ── API Info ──────────────────────────────────────────────────────

@router.get("/")
async def public_api_info():
    return {
        "name": "School Management System Public API",
        "version": "1.0.0",
        "documentation": "/docs",
        "authentication": "X-API-Key header",
        "rate_limit": "1000 requests/minute per school",
        "endpoints": {
            "students": "/public/v1/students",
            "attendance": "/public/v1/attendance",
            "marks": "/public/v1/marks",
            "teachers": "/public/v1/teachers",
            "webhooks": "/public/v1/webhooks/attendance",
        },
    }
