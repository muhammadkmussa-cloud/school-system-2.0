"""School Management System — Advanced Dashboard & Analytics Engine.

Produces rich, multi-dimensional analytics for school administrators:
- Performance heatmaps (subject × class)
- Trend analysis with moving averages
- Comparative analytics (class vs class, term vs term)
- Early warning indicators (at-risk students)
- Executive summary with key metrics
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select, case, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student import Student
from app.models.teacher import Teacher
from app.models.attendance import AttendanceRecord
from app.models.assessment import Assessment, Mark
from app.models.lesson import LessonPlan
from app.models.academic import Class_, Subject, Stream, Term


class AdvancedDashboardService:
    """School intelligence engine for administrator dashboards."""

    def __init__(self, db: AsyncSession, school_id: uuid.UUID):
        self.db = db
        self.school_id = school_id

    # ── Executive Summary ─────────────────────────────────────────

    async def executive_summary(self) -> dict[str, Any]:
        """One-page snapshot with all KPIs."""
        today = date.today()
        month_start = today.replace(day=1)
        week_start = today - timedelta(days=today.weekday())

        # Basic counts
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

        # Gender ratio
        male = await self.db.scalar(
            select(func.count(Student.id)).where(
                Student.school_id == self.school_id, Student.status == "active",
                Student.gender == "male",
            )
        )
        female = await self.db.scalar(
            select(func.count(Student.id)).where(
                Student.school_id == self.school_id, Student.status == "active",
                Student.gender == "female",
            )
        )

        # Today's attendance
        today_records = await self.db.scalars(
            select(AttendanceRecord).join(Student).where(
                Student.school_id == self.school_id,
                AttendanceRecord.attendance_date == today,
            )
        )
        rlist = list(today_records)
        present_today = sum(1 for r in rlist if r.status == "present")

        # This week's assessments
        week_assessments = await self.db.scalar(
            select(func.count(Assessment.id)).where(
                Assessment.school_id == self.school_id,
                Assessment.created_at >= week_start,
            )
        )

        # This month's lessons
        month_lessons = await self.db.scalar(
            select(func.count(LessonPlan.id)).where(
                LessonPlan.school_id == self.school_id,
                LessonPlan.created_at >= month_start,
            )
        )
        month_completed = await self.db.scalar(
            select(func.count(LessonPlan.id)).where(
                LessonPlan.school_id == self.school_id,
                LessonPlan.created_at >= month_start,
                LessonPlan.completion_status == "completed",
            )
        )

        # Current term
        current_term = await self.db.scalar(
            select(Term).join(AcademicYear).where(
                AcademicYear.school_id == self.school_id,
                Term.is_current == True,
            )
        )
        current_term_id = str(current_term.id) if current_term else None

        # Active classes
        class_count = await self.db.scalar(
            select(func.count(Class_.id)).where(Class_.school_id == self.school_id)
        )

        # Attendance trend (last 7 days)
        trend = []
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            day_records = await self.db.scalars(
                select(AttendanceRecord).join(Student).where(
                    Student.school_id == self.school_id,
                    AttendanceRecord.attendance_date == d,
                )
            )
            dl = list(day_records)
            p = sum(1 for r in dl if r.status == "present")
            trend.append({
                "date": str(d),
                "present": p,
                "total": len(dl),
                "rate": round((p / len(dl) * 100) if dl else 0, 1),
            })

        return {
            "current_term_id": current_term_id,
            "students": {
                "total": total_students or 0,
                "male": male or 0,
                "female": female or 0,
                "ratio": f"{male or 0}:{female or 0}",
            },
            "teachers": total_teachers or 0,
            "classes": class_count or 0,
            "attendance_today": {
                "present": present_today,
                "total": len(rlist),
                "rate": round((present_today / len(rlist) * 100) if rlist else 0, 1),
            },
            "attendance_trend": trend,
            "assessments_this_week": week_assessments or 0,
            "lessons_this_month": {
                "total": month_lessons or 0,
                "completed": month_completed or 0,
                "rate": round((month_completed / (month_lessons or 1)) * 100, 1),
            },
        }

    # ── Performance Heatmap ────────────────────────────────────────

    async def performance_heatmap(self, term_id: uuid.UUID) -> dict[str, Any]:
        """Subject × Class performance matrix."""
        classes = await self.db.scalars(
            select(Class_).where(Class_.school_id == self.school_id).order_by(Class_.level)
        )
        subjects = await self.db.scalars(
            select(Subject).where(Subject.school_id == self.school_id).order_by(Subject.name)
        )
        class_list = list(classes)
        subject_list = list(subjects)

        assessments = await self.db.scalars(
            select(Assessment).where(
                Assessment.school_id == self.school_id,
                Assessment.term_id == term_id,
            )
        )
        a_list = list(assessments)

        # Build matrix
        grid: dict[str, dict[str, dict]] = {}
        for klass in class_list:
            grid[klass.name] = {}
            for subj in subject_list:
                avg = await self._subject_class_average(
                    subj.id, klass.id, a_list
                )
                grid[klass.name][subj.name] = {
                    "average": avg,
                    "grade": self._grade_from_mean(avg),
                }

        return {
            "term_id": str(term_id),
            "classes": [c.name for c in class_list],
            "subjects": [s.name for s in subject_list],
            "matrix": grid,
        }

    async def _subject_class_average(
        self, subject_id: uuid.UUID, class_id: uuid.UUID, assessments: list[Assessment]
    ) -> float:
        """Compute average percentage for a subject in a class."""
        relevant = [a for a in assessments if a.subject_id == subject_id and a.class_id == class_id]
        if not relevant:
            return 0.0

        mark_values: list[float] = []
        for a in relevant:
            marks = await self.db.scalars(
                select(Mark).where(Mark.assessment_id == a.id)
            )
            for m in marks:
                pct = (m.score / a.max_score * 100) if a.max_score else 0
                mark_values.append(pct)

        if not mark_values:
            return 0.0
        return round(sum(mark_values) / len(mark_values), 2)

    def _grade_from_mean(self, mean: float) -> str:
        if mean >= 80: return "A"
        elif mean >= 65: return "B"
        elif mean >= 50: return "C"
        elif mean >= 35: return "D"
        return "E"

    # ── At-Risk Students ───────────────────────────────────────────

    async def at_risk_students(
        self, term_id: uuid.UUID, threshold: float = 40.0
    ) -> list[dict]:
        """Identify students below academic threshold and/or with poor attendance."""
        students = await self.db.scalars(
            select(Student).where(
                Student.school_id == self.school_id,
                Student.status == "active",
            )
        )
        student_list = list(students)

        at_risk: list[dict] = []
        for s in student_list:
            reasons: list[str] = []

            # Check academic performance
            mean = await self._compute_student_mean(s.id, term_id)
            if mean < threshold:
                reasons.append(f"Academic: {mean:.1f}% (below {threshold}%)")

            # Check attendance (last 30 days)
            att_rate = await self._attendance_rate(s.id, 30)
            if att_rate < 75:
                reasons.append(f"Attendance: {att_rate:.0f}%")

            if reasons:
                at_risk.append({
                    "student_id": str(s.id),
                    "name": s.full_name,
                    "admission_number": s.admission_number,
                    "class_id": str(s.class_id),
                    "mean": round(mean, 1),
                    "attendance_rate": round(att_rate, 1),
                    "reasons": reasons,
                    "risk_level": "high" if len(reasons) >= 2 else "medium",
                })

        at_risk.sort(key=lambda x: x["mean"])
        return at_risk

    async def _compute_student_mean(self, student_id: uuid.UUID, term_id: uuid.UUID) -> float:
        assessments = await self.db.scalars(
            select(Assessment).where(Assessment.term_id == term_id)
        )
        a_list = list(assessments)
        total = 0.0
        max_p = 0.0
        for a in a_list:
            mark = await self.db.scalar(
                select(Mark).where(Mark.assessment_id == a.id, Mark.student_id == student_id)
            )
            sc = mark.score if mark else 0.0
            total += sc * a.weight
            max_p += a.max_score * a.weight
        return (total / max_p * 100) if max_p > 0 else 0.0

    async def _attendance_rate(self, student_id: uuid.UUID, days: int) -> float:
        cutoff = date.today() - timedelta(days=days)
        records = await self.db.scalars(
            select(AttendanceRecord).where(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.attendance_date >= cutoff,
            )
        )
        rlist = list(records)
        if not rlist:
            return 100.0
        present = sum(1 for r in rlist if r.status == "present")
        return (present / len(rlist)) * 100

    # ── Term Comparison ────────────────────────────────────────────

    async def term_comparison(
        self, term1_id: uuid.UUID, term2_id: uuid.UUID
    ) -> dict[str, Any]:
        """Compare performance between two terms."""
        async def term_stats(tid: uuid.UUID):
            assessments = await self.db.scalars(
                select(Assessment).where(
                    Assessment.school_id == self.school_id,
                    Assessment.term_id == tid,
                )
            )
            a_list = list(assessments)
            scores: list[float] = []
            for a in a_list:
                marks = await self.db.scalars(
                    select(Mark).where(Mark.assessment_id == a.id)
                )
                for m in marks:
                    pct = (m.score / a.max_score * 100) if a.max_score else 0
                    scores.append(pct)

            if not scores:
                return {"average": 0, "count": 0, "pass_rate": 0}

            avg = round(sum(scores) / len(scores), 2)
            passed = sum(1 for s in scores if s >= 35)
            return {
                "average": avg,
                "count": len(scores),
                "pass_rate": round((passed / len(scores)) * 100, 1),
            }

        t1 = await term_stats(term1_id)
        t2 = await term_stats(term2_id)

        # Load term names
        t1_name = "Term 1"
        t2_name = "Term 2"
        t1_obj = await self.db.scalar(select(Term).where(Term.id == term1_id))
        t2_obj = await self.db.scalar(select(Term).where(Term.id == term2_id))
        if t1_obj: t1_name = t1_obj.name
        if t2_obj: t2_name = t2_obj.name

        return {
            "term1": {"name": t1_name, **t1},
            "term2": {"name": t2_name, **t2},
            "change": {
                "average_delta": round(t2["average"] - t1["average"], 2),
                "pass_rate_delta": round(t2["pass_rate"] - t1["pass_rate"], 1),
                "direction": "up" if t2["average"] > t1["average"] else "down",
            },
        }

    # ── Stream Comparison ──────────────────────────────────────────

    async def stream_comparison(
        self, class_id: uuid.UUID, term_id: uuid.UUID
    ) -> list[dict]:
        """Compare performance across streams within a class."""
        streams = await self.db.scalars(
            select(Stream).where(
                Stream.school_id == self.school_id,
                Stream.class_id == class_id,
            )
        )
        stream_list = list(streams)

        result = []
        for stream in stream_list:
            students = await self.db.scalars(
                select(Student).where(
                    Student.stream_id == stream.id,
                    Student.status == "active",
                )
            )
            s_list = list(students)

            means = []
            for s in s_list:
                m = await self._compute_student_mean(s.id, term_id)
                means.append(m)

            result.append({
                "stream_name": stream.name,
                "students": len(s_list),
                "average": round(sum(means) / len(means), 2) if means else 0,
                "highest": round(max(means), 2) if means else 0,
                "lowest": round(min(means), 2) if means else 0,
            })

        result.sort(key=lambda x: x["average"], reverse=True)
        return result

    # ── Teacher Leaderboard ────────────────────────────────────────

    async def teacher_leaderboard(self, term_id: uuid.UUID) -> list[dict]:
        """Rank teachers by composite score (student perf + lesson completion + attendance rate)."""
        teachers = await self.db.scalars(
            select(Teacher).where(
                Teacher.school_id == self.school_id,
                Teacher.is_active == True,
            )
        )
        t_list = list(teachers)

        leaderboard = []
        for t in t_list:
            # Student performance
            assessments = await self.db.scalars(
                select(Assessment).where(
                    Assessment.teacher_id == t.id,
                    Assessment.term_id == term_id,
                )
            )
            a_list = list(assessments)
            perf_scores: list[float] = []
            for a in a_list:
                marks = await self.db.scalars(
                    select(Mark).where(Mark.assessment_id == a.id)
                )
                for m in marks:
                    perf_scores.append(
                        (m.score / a.max_score * 100) if a.max_score else 0
                    )

            avg_perf = round(sum(perf_scores) / len(perf_scores), 2) if perf_scores else 0

            # Lesson completion
            total_lessons = await self.db.scalar(
                select(func.count(LessonPlan.id)).where(LessonPlan.teacher_id == t.id)
            )
            completed = await self.db.scalar(
                select(func.count(LessonPlan.id)).where(
                    LessonPlan.teacher_id == t.id,
                    LessonPlan.completion_status == "completed",
                )
            )
            lesson_rate = round(
                (completed / (total_lessons or 1)) * 100, 1
            )

            # Composite score
            composite = round((avg_perf * 0.6) + (lesson_rate * 0.4), 2)

            leaderboard.append({
                "teacher_id": str(t.id),
                "name": t.full_name,
                "avg_performance": avg_perf,
                "lesson_completion_rate": lesson_rate,
                "composite_score": composite,
                "students_assessed": len(perf_scores),
            })

        leaderboard.sort(key=lambda x: x["composite_score"], reverse=True)
        return leaderboard
