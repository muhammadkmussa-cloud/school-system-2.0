"""School Management System — Mobile-Optimized API.

Thin, paginated endpoints designed for Flutter mobile consumption.
Returns minimal payloads with only the fields a teacher needs.
Every endpoint supports `?since=` for delta syncs.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func

from app.core.config import settings
from app.core.dependencies import CurrentUser, DB, RequireStaff
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.attendance import AttendanceRecord
from app.models.assessment import Assessment, Mark
from app.models.lesson import LessonPlan
from app.models.timetable import Timetable, TimetableEntry

router = APIRouter(prefix="/mobile", tags=["Mobile"])


# ── Teacher Context ──────────────────────────────────────────────────

async def _get_teacher(db, current_user):
    return await db.scalar(
        select(Teacher).where(
            Teacher.user_id == current_user.id,
            Teacher.school_id == current_user.school_id,
        )
    )


# ── My Students (minimal) ───────────────────────────────────────────

@router.get("/my-students")
async def my_students(
    db: DB,
    current_user: RequireStaff,
    since: str = Query("", description="ISO datetime — only return changes after this"),
):
    """Minimal student list for attendance/marks entry on mobile."""
    teacher = await _get_teacher(db, current_user)
    if not teacher:
        return {"students": []}

    # Find classes this teacher is assigned to via timetable
    entries = await db.scalars(
        select(TimetableEntry).where(TimetableEntry.teacher_id == teacher.id)
    )
    class_ids = list({e.class_id for e in entries})

    base = select(Student).where(
        Student.school_id == current_user.school_id,
        Student.status == "active",
    )
    if class_ids:
        base = base.where(Student.class_id.in_(class_ids))
    if since:
        base = base.where(Student.updated_at >= datetime.fromisoformat(since))

    rows = (await db.scalars(base.order_by(Student.full_name).limit(settings.MOBILE_STUDENT_LIST_LIMIT))).all()

    return {
        "students": [
            {
                "id": str(s.id),
                "admission_number": s.admission_number,
                "full_name": s.full_name,
                "gender": s.gender,
                "class_id": str(s.class_id),
                "stream_id": str(s.stream_id) if s.stream_id else None,
            }
            for s in rows
        ],
        "total": len(rows),
    }


# ── Today's Timetable (mobile card) ─────────────────────────────────

@router.get("/today")
async def today_summary(db: DB, current_user: RequireStaff):
    """Everything a teacher needs for today — timetable, pending attendance."""
    teacher = await _get_teacher(db, current_user)
    if not teacher:
        return {"timetable": [], "pending_attendance": []}

    today = date.today()
    day_of_week = today.weekday()

    # Find active timetable
    timetable = await db.scalar(
        select(Timetable).where(
            Timetable.school_id == current_user.school_id,
            Timetable.is_active == True,
        )
    )

    lessons = []
    pending = []

    if timetable:
        entries = await db.scalars(
            select(TimetableEntry).where(
                TimetableEntry.timetable_id == timetable.id,
                TimetableEntry.teacher_id == teacher.id,
                TimetableEntry.day_of_week == day_of_week,
            ).order_by(TimetableEntry.start_time)
        )

        for e in entries:
            # Check if attendance already recorded
            existing = await db.scalar(
                select(func.count(AttendanceRecord.id)).where(
                    AttendanceRecord.class_id == e.class_id,
                    AttendanceRecord.attendance_date == today,
                )
            )

            lessons.append({
                "class_id": str(e.class_id),
                "subject_id": str(e.subject_id),
                "start": str(e.start_time)[:5],
                "end": str(e.end_time)[:5],
                "room": e.room,
                "attendance_done": (existing or 0) > 0,
            })

            if not existing:
                pending.append(str(e.class_id))

    return {
        "date": str(today),
        "day_name": today.strftime("%A"),
        "timetable": lessons,
        "pending_attendance": pending,
        "total_lessons": len(lessons),
    }


# ── Quick Attendance (batch-optimized) ──────────────────────────────

@router.post("/quick-attendance")
async def quick_attendance(payload: dict, db: DB, current_user: RequireStaff):
    """Minimal attendance recording for mobile — accepts compact payload.

    Payload: {
        "class_id": "...",
        "date": "2026-07-12",
        "records": [
            {"s": "student-uuid", "st": "present"},
            {"s": "student-uuid-2", "st": "absent", "r": "Sick"}
        ]
    }
    s = student_id, st = status, r = remarks (optional)
    """
    class_id = uuid.UUID(payload["class_id"])
    att_date = payload.get("date", str(date.today()))
    records = payload.get("records", [])

    recorded = 0
    for rec in records:
        student_id = uuid.UUID(rec["s"])
        status_val = rec.get("st", "present")
        remarks_val = rec.get("r")

        # Upsert
        existing = await db.scalar(
            select(AttendanceRecord).where(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.attendance_date == att_date,
                AttendanceRecord.school_id == current_user.school_id,
            )
        )
        if existing:
            existing.status = status_val
            existing.remarks = remarks_val
            existing.recorded_by = current_user.id
        else:
            db.add(AttendanceRecord(
                school_id=current_user.school_id,
                student_id=student_id,
                class_id=class_id,
                recorded_by=current_user.id,
                attendance_date=att_date,
                status=status_val,
                remarks=remarks_val,
            ))
        recorded += 1

    await db.flush()
    return {"recorded": recorded, "class_id": str(class_id), "date": att_date}


# ── Quick Marks ─────────────────────────────────────────────────────

@router.post("/quick-marks")
async def quick_marks(payload: dict, db: DB, current_user: RequireStaff):
    """Compact marks entry for mobile.

    Payload: {
        "assessment_id": "...",
        "marks": [
            {"s": "student-uuid", "sc": 85},
            {"s": "student-uuid-2", "sc": 72}
        ]
    }
    s = student_id, sc = score
    """
    assessment_id = uuid.UUID(payload["assessment_id"])
    marks = payload.get("marks", [])

    assessment = await db.scalar(
        select(Assessment).where(
            Assessment.id == assessment_id,
            Assessment.school_id == current_user.school_id,
        )
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")

    recorded = 0
    for m in marks:
        student_id = uuid.UUID(m["s"])
        score = float(m.get("sc", 0))

        existing = await db.scalar(
            select(Mark).where(
                Mark.assessment_id == assessment_id,
                Mark.student_id == student_id,
                Mark.school_id == current_user.school_id,
            )
        )
        if existing:
            existing.score = score
        else:
            from app.core.grading import grade_for
            pct = (score / assessment.max_score * 100) if assessment and assessment.max_score else 0
            letter, _ = grade_for(pct)
            db.add(Mark(
                school_id=current_user.school_id,
                assessment_id=assessment_id,
                student_id=student_id,
                score=score,
                grade=letter,
            ))

        recorded += 1

    await db.flush()
    return {"recorded": recorded, "assessment_id": str(assessment_id)}


# ── My Lessons (compact, sync-friendly) ────────────────────────────

@router.get("/my-lessons")
async def my_lessons(
    db: DB,
    current_user: RequireStaff,
    since: str = Query(""),
    page: int = Query(1, ge=1),
):
    """Teacher's lesson plans — minimal payload for mobile."""
    teacher = await _get_teacher(db, current_user)
    if not teacher:
        return {"lessons": [], "total": 0}

    base = select(LessonPlan).where(
        LessonPlan.teacher_id == teacher.id,
        LessonPlan.school_id == current_user.school_id,
    )
    if since:
        base = base.where(LessonPlan.updated_at >= datetime.fromisoformat(since))

    total = await db.scalar(select(func.count()).select_from(base.subquery()))
    rows = (await db.scalars(
        base.order_by(LessonPlan.created_at.desc())
        .offset((page - 1) * 50).limit(50)
    )).all()

    return {
        "lessons": [
            {
                "id": str(l.id),
                "topic": l.topic,
                "subject_id": str(l.subject_id),
                "class_id": str(l.class_id),
                "status": l.completion_status,
                "week": l.week_number,
                "updated": l.updated_at.isoformat(),
            }
            for l in rows
        ],
        "total": total or 0,
    }


# ── Sync checkpoint ─────────────────────────────────────────────────

@router.get("/sync-checkpoint")
async def sync_checkpoint(db: DB, current_user: RequireStaff):
    """Return a timestamp token clients can use for `?since=` in all mobile endpoints."""
    now = datetime.utcnow().isoformat()
    return {
        "sync_token": now,
        "school_id": str(current_user.school_id),
        "user_id": str(current_user.id),
        "message": "Use this token as the `since` parameter in subsequent requests.",
    }
