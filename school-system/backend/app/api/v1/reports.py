"""Report generation routes."""

from __future__ import annotations

import io
import uuid
from datetime import date

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.core.dependencies import DB, RequireSchoolAdmin, RequireStaff
from app.models.assessment import Assessment, Mark
from app.models.attendance import AttendanceRecord
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.lesson import LessonPlan

router = APIRouter()


@router.get("/attendance")
async def attendance_report(
    db: DB,
    current_user: RequireStaff,
    class_id: str = "",
    from_date: str = "",
    to_date: str = "",
    format: str = "json",
):
    """Generate attendance report."""
    base = (
        select(AttendanceRecord)
        .join(Student)
        .where(Student.school_id == current_user.school_id)
    )
    if class_id:
        base = base.where(AttendanceRecord.class_id == uuid.UUID(class_id))
    if from_date:
        base = base.where(AttendanceRecord.attendance_date >= date.fromisoformat(from_date))
    if to_date:
        base = base.where(AttendanceRecord.attendance_date <= date.fromisoformat(to_date))

    records_list = list(await db.scalars(base.order_by(AttendanceRecord.attendance_date.desc())))

    if format == "csv":
        import csv

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Date", "Student ID", "Class ID", "Status", "Remarks"])
        for r in records_list:
            writer.writerow([r.attendance_date, r.student_id, r.class_id, r.status, r.remarks or ""])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=attendance_report.csv"},
        )

    return {
        "records": [
            {
                "date": str(r.attendance_date),
                "student_id": str(r.student_id),
                "class_id": str(r.class_id),
                "status": r.status,
                "remarks": r.remarks,
            }
            for r in records_list
        ],
        "total": len(records_list),
    }


@router.get("/students")
async def student_report(
    db: DB,
    current_user: RequireStaff,
    class_id: str = "",
    status: str = "active",
    format: str = "json",
):
    """Generate student list report."""
    base = select(Student).where(
        Student.school_id == current_user.school_id, Student.status == status
    )
    if class_id:
        base = base.where(Student.class_id == uuid.UUID(class_id))

    students_list = list(await db.scalars(base.order_by(Student.full_name)))

    if format == "csv":
        import csv

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Admission #", "Full Name", "Gender", "Class", "Status"])
        for s in students_list:
            writer.writerow([s.admission_number, s.full_name, s.gender, str(s.class_id), s.status])
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=student_list.csv"},
        )

    return {
        "students": [
            {
                "id": str(s.id),
                "admission_number": s.admission_number,
                "full_name": s.full_name,
                "gender": s.gender,
                "class_id": str(s.class_id),
                "status": s.status,
            }
            for s in students_list
        ],
        "total": len(students_list),
    }


@router.get("/teacher-workload")
async def teacher_workload_report(db: DB, current_user: RequireSchoolAdmin):
    """Show teacher workload — lessons, assessments, and timetable entries."""
    teachers = await db.scalars(
        select(Teacher).where(Teacher.school_id == current_user.school_id)
    )
    teacher_list = teachers.all()

    result = []
    for t in teacher_list:
        lesson_count = await db.scalar(
            select(func.count(LessonPlan.id)).where(LessonPlan.teacher_id == t.id)
        )
        assessment_count = await db.scalar(
            select(func.count(Assessment.id)).where(Assessment.teacher_id == t.id)
        )
        result.append(
            {
                "teacher_id": str(t.id),
                "name": t.full_name,
                "employee_number": t.employee_number,
                "lessons": lesson_count or 0,
                "assessments": assessment_count or 0,
            }
        )

    return {"teachers": result}


@router.get("/subject-performance")
async def subject_performance_report(
    db: DB,
    current_user: RequireSchoolAdmin,
    term_id: str = "",
):
    """Subject performance aggregated across the school."""
    base = select(Assessment).where(Assessment.school_id == current_user.school_id)
    if term_id:
        base = base.where(Assessment.term_id == uuid.UUID(term_id))

    assessments = await db.scalars(base)
    assessment_list = assessments.all()

    subject_stats: dict[str, dict] = {}
    for a in assessment_list:
        marks = await db.scalars(select(Mark).where(Mark.assessment_id == a.id))
        scores = [m.score for m in marks]
        if scores:
            sid = str(a.subject_id)
            if sid not in subject_stats:
                subject_stats[sid] = {"total": 0, "count": 0, "highest": 0, "lowest": 1000}
            subject_stats[sid]["total"] += sum(scores)
            subject_stats[sid]["count"] += len(scores)
            subject_stats[sid]["highest"] = max(subject_stats[sid]["highest"], max(scores))
            subject_stats[sid]["lowest"] = min(subject_stats[sid]["lowest"], min(scores))

    return {
        "subjects": [
            {
                "subject_id": sid,
                "average": round(stats["total"] / stats["count"], 2) if stats["count"] else 0,
                "highest": stats["highest"],
                "lowest": stats["lowest"] if stats["lowest"] != 1000 else 0,
                "total_marks_recorded": stats["count"],
            }
            for sid, stats in subject_stats.items()
        ]
    }
