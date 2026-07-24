"""Dashboard routes — aggregated metrics for admin & teacher views."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.dependencies import CurrentUser, DB, RequireStaff
from app.models.assessment import Assessment
from app.models.attendance import AttendanceRecord
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.timetable import TimetableEntry
from app.models.lesson import LessonPlan

router = APIRouter()


@router.get("/admin")
async def admin_dashboard(db: DB, current_user: RequireStaff):
    """Dashboard for school administrators."""
    school_id = current_user.school_id
    today = date.today()

    total_students = await db.scalar(
        select(func.count(Student.id)).where(
            Student.school_id == school_id, Student.status == "active"
        )
    )
    total_teachers = await db.scalar(
        select(func.count(Teacher.id)).where(
            Teacher.school_id == school_id, Teacher.is_active == True
        )
    )
    from app.models.academic import Class_
    total_classes = await db.scalar(
        select(func.count(Class_.id)).where(Class_.school_id == school_id)
    )

    # Today's attendance
    today_attendance = await db.scalars(
        select(AttendanceRecord).where(
            AttendanceRecord.attendance_date == today,
        ).join(Student).where(Student.school_id == school_id)
    )
    att_records = today_attendance.all()
    present = sum(1 for r in att_records if r.status == "present")
    total_att = len(att_records)

    # Recent assessments
    recent_assessments = await db.scalar(
        select(func.count(Assessment.id)).where(
            Assessment.school_id == school_id,
            Assessment.created_at >= datetime.utcnow() - timedelta(days=30),
        )
    )

    return {
        "total_students": total_students or 0,
        "total_teachers": total_teachers or 0,
        "total_classes": total_classes or 0,
        "attendance_today": {
            "present": present,
            "total": total_att,
            "percentage": round((present / total_att * 100) if total_att else 0, 1),
        },
        "recent_assessments": recent_assessments or 0,
    }


@router.get("/teacher")
async def teacher_dashboard(db: DB, current_user: RequireStaff):
    """Dashboard for teachers."""
    from app.models.teacher import Teacher

    teacher = await db.scalar(
        select(Teacher).where(Teacher.user_id == current_user.id)
    )
    if not teacher:
        return {"message": "No teacher profile linked"}

    today = date.today()
    day_of_week = today.weekday()

    # Today's timetable
    today_lessons = await db.scalars(
        select(TimetableEntry).where(
            TimetableEntry.teacher_id == teacher.id,
            TimetableEntry.day_of_week == day_of_week,
        ).order_by(TimetableEntry.start_time)
    )

    # Pending attendance (classes taught today that don't have attendance)
    pending_classes = []
    for entry in today_lessons:
        existing = await db.scalar(
            select(func.count(AttendanceRecord.id)).where(
                AttendanceRecord.class_id == entry.class_id,
                AttendanceRecord.attendance_date == today,
            )
        )
        if not existing:
            pending_classes.append(str(entry.class_id))

    # Recent lesson plans
    recent_lessons = await db.scalar(
        select(func.count(LessonPlan.id)).where(
            LessonPlan.teacher_id == teacher.id,
            LessonPlan.created_at >= datetime.utcnow() - timedelta(days=7),
        )
    )

    return {
        "today_timetable": [
            {
                "subject_id": str(e.subject_id),
                "class_id": str(e.class_id),
                "start": str(e.start_time),
                "end": str(e.end_time),
                "room": e.room,
            }
            for e in today_lessons
        ],
        "pending_attendance": pending_classes,
        "lessons_this_week": recent_lessons or 0,
    }
