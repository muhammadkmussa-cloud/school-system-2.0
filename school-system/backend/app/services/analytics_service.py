"""School Management System — Advanced Analytics.

Produces school-wide and teacher-specific analytics including:
- Pass rates over time
- Attendance trends
- Gender performance analysis
- Teacher effectiveness metrics
- Syllabus coverage tracking
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assessment import Assessment, Mark
from app.models.attendance import AttendanceRecord
from app.models.lesson import LessonPlan
from app.models.student import Student
from app.models.teacher import Teacher


class AnalyticsService:
    """School intelligence dashboards."""

    def __init__(self, db: AsyncSession, school_id: uuid.UUID):
        self.db = db
        self.school_id = school_id

    # ── Attendance Analytics ─────────────────────────────────────

    async def attendance_trend(self, days: int = 30) -> dict[str, Any]:
        """Daily attendance percentage over the last N days."""
        today = date.today()
        start = today - timedelta(days=days)

        records = await self.db.scalars(
            select(AttendanceRecord)
            .join(Student)
            .where(
                Student.school_id == self.school_id,
                AttendanceRecord.attendance_date >= start,
            )
            .order_by(AttendanceRecord.attendance_date)
        )
        rlist = list(records)

        daily: dict[str, dict[str, int]] = defaultdict(lambda: {"present": 0, "total": 0})
        for r in rlist:
            key = str(r.attendance_date)
            daily[key]["total"] += 1
            if r.status == "present":
                daily[key]["present"] += 1

        trend = [
            {
                "date": d,
                "present": v["present"],
                "total": v["total"],
                "percentage": round(v["present"] / v["total"] * 100, 1) if v["total"] else 0,
            }
            for d, v in sorted(daily.items())
        ]
        return {"trend": trend, "average_percentage": round(
            sum(t["percentage"] for t in trend) / len(trend), 1
        ) if trend else 0}

    # ── Gender Performance ──────────────────────────────────────

    async def gender_analysis(self, term_id: uuid.UUID) -> dict[str, Any]:
        """Compare male vs female performance across subjects."""
        assessments = await self.db.scalars(
            select(Assessment).where(
                Assessment.school_id == self.school_id,
                Assessment.term_id == term_id,
            )
        )
        a_list = list(assessments)

        gender_scores: dict[str, dict[str, list[float]]] = {
            "male": defaultdict(list),
            "female": defaultdict(list),
        }

        for a in a_list:
            marks = await self.db.scalars(
                select(Mark).where(Mark.assessment_id == a.id)
            )
            for m in marks:
                student = await self.db.scalar(
                    select(Student).where(Student.id == m.student_id)
                )
                if student and student.gender in ("male", "female"):
                    pct = (m.score / a.max_score * 100) if a.max_score else 0
                    gender_scores[student.gender][str(a.subject_id)].append(pct)

        result = {"male": {}, "female": {}}
        for gender in ("male", "female"):
            for subj_id, scores in gender_scores[gender].items():
                result[gender][subj_id] = {
                    "average": round(sum(scores) / len(scores), 2),
                    "count": len(scores),
                }

        return result

    # ── Syllabus Coverage ────────────────────────────────────────

    async def syllabus_coverage(
        self, teacher_id: uuid.UUID | None = None, subject_id: uuid.UUID | None = None
    ) -> dict[str, Any]:
        """How much of the syllabus has been covered (by lessons planned/completed)."""
        filters = [LessonPlan.school_id == self.school_id]
        if teacher_id:
            filters.append(LessonPlan.teacher_id == teacher_id)
        if subject_id:
            filters.append(LessonPlan.subject_id == subject_id)

        total = await self.db.scalar(
            select(func.count(LessonPlan.id)).where(*filters)
        )
        completed = await self.db.scalar(
            select(func.count(LessonPlan.id)).where(
                *filters,
                LessonPlan.completion_status == "completed",
            )
        )
        in_progress = await self.db.scalar(
            select(func.count(LessonPlan.id)).where(
                *filters,
                LessonPlan.completion_status == "in_progress",
            )
        )

        return {
            "total_lessons": total or 0,
            "completed": completed or 0,
            "in_progress": in_progress or 0,
            "planned": (total or 0) - (completed or 0) - (in_progress or 0),
            "completion_percentage": round(
                ((completed or 0) / (total or 1)) * 100, 1
            ),
        }

    # ── Teacher Effectiveness ───────────────────────────────────

    async def teacher_effectiveness(self, term_id: uuid.UUID) -> list[dict[str, Any]]:
        """Rate each teacher by their students' average performance."""
        teachers = await self.db.scalars(
            select(Teacher).where(Teacher.school_id == self.school_id)
        )
        t_list = list(teachers)

        result = []
        for t in t_list:
            assessments = await self.db.scalars(
                select(Assessment).where(
                    Assessment.teacher_id == t.id,
                    Assessment.term_id == term_id,
                )
            )
            a_list = list(assessments)

            if not a_list:
                result.append({
                    "teacher_id": str(t.id),
                    "name": t.full_name,
                    "effectiveness": 0,
                    "students_taught": 0,
                    "assessments_given": 0,
                })
                continue

            scores: list[float] = []
            student_ids: set[uuid.UUID] = set()
            for a in a_list:
                marks = await self.db.scalars(
                    select(Mark).where(Mark.assessment_id == a.id)
                )
                for m in marks:
                    pct = (m.score / a.max_score * 100) if a.max_score else 0
                    scores.append(pct)
                    student_ids.add(m.student_id)

            avg = sum(scores) / len(scores) if scores else 0

            result.append({
                "teacher_id": str(t.id),
                "name": t.full_name,
                "effectiveness": round(avg, 2),
                "students_taught": len(student_ids),
                "assessments_given": len(a_list),
            })

        result.sort(key=lambda x: x["effectiveness"], reverse=True)
        return result

    # ── School Overview ──────────────────────────────────────────

    async def school_overview(self) -> dict[str, Any]:
        """One-page school health dashboard."""
        total_students = await self.db.scalar(
            select(func.count(Student.id)).where(
                Student.school_id == self.school_id, Student.status == "active"
            )
        )
        total_teachers = await self.db.scalar(
            select(func.count(Teacher.id)).where(
                Teacher.school_id == self.school_id, Teacher.is_active == True
            )
        )

        # Gender breakdown
        male = await self.db.scalar(
            select(func.count(Student.id)).where(
                Student.school_id == self.school_id,
                Student.status == "active",
                Student.gender == "male",
            )
        )
        female = await self.db.scalar(
            select(func.count(Student.id)).where(
                Student.school_id == self.school_id,
                Student.status == "active",
                Student.gender == "female",
            )
        )

        # Today's attendance
        today = date.today()
        today_records = await self.db.scalars(
            select(AttendanceRecord).join(Student).where(
                Student.school_id == self.school_id,
                AttendanceRecord.attendance_date == today,
            )
        )
        rlist = list(today_records)
        present = sum(1 for r in rlist if r.status == "present")

        # This month's assessments
        month_start = today.replace(day=1)
        month_assessments = await self.db.scalar(
            select(func.count(Assessment.id)).where(
                Assessment.school_id == self.school_id,
                Assessment.created_at >= month_start,
            )
        )

        # Lessons completed this week
        week_start = today - timedelta(days=today.weekday())
        week_lessons = await self.db.scalar(
            select(func.count(LessonPlan.id)).where(
                LessonPlan.school_id == self.school_id,
                LessonPlan.completion_status == "completed",
                LessonPlan.created_at >= week_start,
            )
        )

        return {
            "students": {
                "total": total_students or 0,
                "male": male or 0,
                "female": female or 0,
            },
            "teachers": total_teachers or 0,
            "attendance_today": {
                "present": present,
                "total": len(rlist),
                "percentage": round((present / len(rlist) * 100) if rlist else 0, 1),
            },
            "assessments_this_month": month_assessments or 0,
            "lessons_completed_this_week": week_lessons or 0,
        }
