"""School Management System — Student Results Engine.

The most critical business module: calculates grades, rankings, means,
position tracking, and generates comprehensive academic analytics.

Supports:
- Per-student cumulative grades across multiple assessments
- Class rankings by subject and overall
- Stream-level aggregation
- Grade distribution analysis
- Term-by-term performance trends
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.grading import compute_term_mean, grade_for
from app.models.assessment import Assessment, Mark
from app.models.student import Student

# ── Data containers ─────────────────────────────────────────────────


@dataclass
class SubjectResult:
    subject_id: str
    subject_name: str
    total_score: float = 0.0
    max_possible: float = 0.0
    percentage: float = 0.0
    grade: str = ""
    points: int = 0
    assessments: list[dict[str, float | str]] = field(default_factory=list)
    rank_in_class: int = 0


@dataclass
class StudentReportCard:
    student_id: str
    student_name: str
    admission_number: str
    class_name: str
    stream_name: str | None
    term_name: str
    academic_year: str
    subjects: list[SubjectResult] = field(default_factory=list)
    overall_total: float = 0.0
    overall_mean: float = 0.0
    overall_grade: str = ""
    overall_points: int = 0
    rank_in_class: int = 0
    total_subjects: int = 0
    teacher_remarks: str = ""
    principal_remarks: str = ""


@dataclass
class ClassPerformanceSummary:
    class_id: str
    class_name: str
    term_id: str
    total_students: int
    subject_averages: dict[str, float] = field(default_factory=dict)
    grade_distribution: dict[str, int] = field(default_factory=dict)
    pass_rate: float = 0.0  # % above D-
    top_performers: list[dict[str, str | float]] = field(default_factory=list)


# ── Engine ──────────────────────────────────────────────────────────


class ResultsEngine:
    """High-performance grading engine with caching support."""

    def __init__(self, db: AsyncSession, school_id: uuid.UUID):
        self.db = db
        self.school_id = school_id

    async def compute_student_report(
        self,
        student_id: uuid.UUID,
        term_id: uuid.UUID,
    ) -> StudentReportCard | None:
        """Generate a full report card for one student in one term."""

        student = await self.db.scalar(
            select(Student).where(
                Student.id == student_id,
                Student.school_id == self.school_id,
            )
        )
        if not student:
            return None

        # Load class & stream names
        class_name = "—"
        stream_name: str | None = None
        term_name = "—"
        acad_year = "—"

        from app.models.academic import Class_, Stream, Term, AcademicYear
        klass = await self.db.scalar(select(Class_).where(Class_.id == student.class_id))
        if klass:
            class_name = klass.name

        if student.stream_id:
            st = await self.db.scalar(select(Stream).where(Stream.id == student.stream_id))
            if st:
                stream_name = st.name

        term = await self.db.scalar(select(Term).where(Term.id == term_id))
        if term:
            term_name = term.name
            ay = await self.db.scalar(select(AcademicYear).where(AcademicYear.id == term.academic_year_id))
            if ay:
                acad_year = ay.name

        # Fetch all assessments for this class/term
        assessments = await self.db.scalars(
            select(Assessment).where(
                Assessment.school_id == self.school_id,
                Assessment.class_id == student.class_id,
                Assessment.term_id == term_id,
            )
        )
        assessment_list = list(assessments)

        # Group assessments by subject
        by_subject: dict[uuid.UUID, list[Assessment]] = defaultdict(list)
        for a in assessment_list:
            by_subject[a.subject_id].append(a)

        # Load subject names
        from app.models.academic import Subject
        subject_names: dict[uuid.UUID, str] = {}
        all_subject_ids = list(by_subject.keys())
        if all_subject_ids:
            subs = await self.db.scalars(
                select(Subject).where(Subject.id.in_(all_subject_ids))
            )
            for s in subs:
                subject_names[s.id] = s.name

        # Batch-load all marks for the student in one query
        all_marks = await self.db.scalars(
            select(Mark).where(
                Mark.assessment_id.in_([a.id for a in assessment_list]),
                Mark.student_id == student_id,
            )
        )
        marks_by_assessment: dict[uuid.UUID, Mark] = {}
        for m in all_marks:
            marks_by_assessment[m.assessment_id] = m

        # Compute per-subject
        subject_results: list[SubjectResult] = []
        total_points = 0
        total_pct_sum = 0.0

        for subject_id, assessments_for_subj in by_subject.items():
            total_score = 0.0
            max_possible = 0.0
            detail = []

            for a in assessments_for_subj:
                mark = marks_by_assessment.get(a.id)
                score = mark.score if mark else 0.0
                weighted_score = score * a.weight
                weighted_max = a.max_score * a.weight
                total_score += weighted_score
                max_possible += weighted_max
                detail.append({
                    "assessment": a.name,
                    "type": a.assessment_type,
                    "score": score,
                    "max": a.max_score,
                    "weight": a.weight,
                })

            pct = (total_score / max_possible * 100) if max_possible > 0 else 0.0
            letter, points = grade_for(pct)
            total_points += points
            total_pct_sum += pct

            subject_results.append(SubjectResult(
                subject_id=str(subject_id),
                subject_name=subject_names.get(subject_id, "Unknown"),
                total_score=round(total_score, 2),
                max_possible=round(max_possible, 2),
                percentage=round(pct, 2),
                grade=letter,
                points=points,
                assessments=detail,
            ))

        num_subjects = len(subject_results) or 1
        overall_mean = compute_term_mean(total_pct_sum, num_subjects)
        overall_grade, overall_points = grade_for(overall_mean)

        # Compute class rank
        rank = await self._compute_class_rank(student, term_id, overall_mean)

        # Remarks
        teacher_remarks = self._generate_teacher_remarks(overall_mean)
        principal_remarks = self._generate_principal_remarks(overall_mean)

        return StudentReportCard(
            student_id=str(student.id),
            student_name=student.full_name,
            admission_number=student.admission_number,
            class_name=class_name,
            stream_name=stream_name,
            term_name=term_name,
            academic_year=acad_year,
            subjects=subject_results,
            overall_total=round(total_pct_sum, 2),
            overall_mean=overall_mean,
            overall_grade=overall_grade,
            overall_points=overall_points,
            rank_in_class=rank,
            total_subjects=num_subjects,
            teacher_remarks=teacher_remarks,
            principal_remarks=principal_remarks,
        )

    async def _compute_class_rank(
        self,
        student: Student,
        term_id: uuid.UUID,
        student_mean: float,
    ) -> int:
        """Determine the student's position in class by overall mean."""
        classmates = await self.db.scalars(
            select(Student).where(
                Student.class_id == student.class_id,
                Student.school_id == self.school_id,
                Student.status == "active",
            )
        )
        classmate_ids = [c.id for c in classmates if c.id != student.id]

        # Batch-load all marks for all classmates in one query
        if classmate_ids:
            assessments = await self.db.scalars(
                select(Assessment).where(Assessment.term_id == term_id)
            )
            a_list = list(assessments)
            if a_list:
                all_marks = await self.db.scalars(
                    select(Mark).where(
                        Mark.assessment_id.in_([a.id for a in a_list]),
                        Mark.student_id.in_(classmate_ids),
                    )
                )
                marks_by_key: dict[tuple[uuid.UUID, uuid.UUID], Mark] = {}
                for m in all_marks:
                    marks_by_key[(m.student_id, m.assessment_id)] = m

                # Compute mean per classmate
                means: list[float] = [student_mean]
                for cid in classmate_ids:
                    total_score = 0.0
                    max_possible = 0.0
                    for a in a_list:
                        mark = marks_by_key.get((cid, a.id))
                        sc = mark.score if mark else 0.0
                        total_score += sc * a.weight
                        max_possible += a.max_score * a.weight
                    means.append((total_score / max_possible * 100) if max_possible > 0 else 0.0)
            else:
                means = [student_mean] + [0.0] * len(classmate_ids)
        else:
            means = [student_mean]

        sorted_means = sorted(means, reverse=True)
        try:
            return sorted_means.index(student_mean) + 1
        except ValueError:
            return len(sorted_means)

    async def compute_mean_for_student(
        self, student_id: uuid.UUID, term_id: uuid.UUID
    ) -> float:
        """Compute a student's overall mean percentage for a term."""
        assessments = await self.db.scalars(
            select(Assessment).where(Assessment.term_id == term_id)
        )
        a_list = list(assessments)

        if not a_list:
            return 0.0

        # Batch-load all marks for this student
        all_marks = await self.db.scalars(
            select(Mark).where(
                Mark.assessment_id.in_([a.id for a in a_list]),
                Mark.student_id == student_id,
            )
        )
        marks_by_assessment: dict[uuid.UUID, Mark] = {}
        for m in all_marks:
            marks_by_assessment[m.assessment_id] = m

        total_score = 0.0
        max_possible = 0.0

        for a in a_list:
            mark = marks_by_assessment.get(a.id)
            score = mark.score if mark else 0.0
            total_score += score * a.weight
            max_possible += a.max_score * a.weight

        return (total_score / max_possible * 100) if max_possible > 0 else 0.0

    async def compute_class_summary(
        self, class_id: uuid.UUID, term_id: uuid.UUID
    ) -> ClassPerformanceSummary:
        """Generate aggregated performance stats for an entire class."""

        from app.models.academic import Class_, Subject
        klass = await self.db.scalar(select(Class_).where(Class_.id == class_id))
        class_name = klass.name if klass else "—"

        students = await self.db.scalars(
            select(Student).where(
                Student.class_id == class_id,
                Student.school_id == self.school_id,
                Student.status == "active",
            )
        )
        student_list = list(students)

        assessments = await self.db.scalars(
            select(Assessment).where(
                Assessment.class_id == class_id,
                Assessment.term_id == term_id,
            )
        )
        a_list = list(assessments)
        if not a_list or not student_list:
            return ClassPerformanceSummary(
                class_id=str(class_id), class_name=class_name, term_id=str(term_id),
                total_students=len(student_list), subject_averages={},
                grade_distribution={}, pass_rate=0.0, top_performers=[],
            )

        # Batch-load all marks for all students in one query
        all_marks = await self.db.scalars(
            select(Mark).where(
                Mark.assessment_id.in_([a.id for a in a_list]),
                Mark.student_id.in_([s.id for s in student_list]),
            )
        )
        marks_by_student_assessment: dict[tuple[uuid.UUID, uuid.UUID], Mark] = {}
        for m in all_marks:
            marks_by_student_assessment[(m.student_id, m.assessment_id)] = m

        # Batch-load subject names
        all_subject_ids = list({a.subject_id for a in a_list})
        subjects = await self.db.scalars(
            select(Subject).where(Subject.id.in_(all_subject_ids))
        )
        subject_names: dict[uuid.UUID, str] = {s.id: s.name for s in subjects}

        # Build per-student data
        grade_dist: dict[str, int] = defaultdict(int)
        student_means: dict[uuid.UUID, float] = {}
        by_subject: dict[uuid.UUID, list[float]] = defaultdict(list)

        for s in student_list:
            total_score = 0.0
            max_possible = 0.0
            subj_scores: dict[uuid.UUID, float] = defaultdict(float)
            subj_max: dict[uuid.UUID, float] = defaultdict(float)

            for a in a_list:
                mark = marks_by_student_assessment.get((s.id, a.id))
                sc = mark.score if mark else 0.0
                total_score += sc * a.weight
                max_possible += a.max_score * a.weight
                subj_scores[a.subject_id] += sc * a.weight
                subj_max[a.subject_id] += a.max_score * a.weight

            mean = (total_score / max_possible * 100) if max_possible > 0 else 0.0
            student_means[s.id] = mean
            letter, _ = grade_for(mean)
            grade_dist[letter] += 1

            for sid in set(a.subject_id for a in a_list):
                pct = (subj_scores[sid] / subj_max[sid] * 100) if subj_max[sid] > 0 else 0.0
                by_subject[sid].append(pct)

        subject_avgs: dict[str, float] = {}
        for sid, pcts in by_subject.items():
            avg = round(sum(pcts) / len(pcts), 2) if pcts else 0.0
            subject_avgs[subject_names.get(sid, str(sid)[:8])] = avg

        total = sum(grade_dist.values()) or 1
        pass_count = sum(
            cnt for g, cnt in grade_dist.items()
            if g not in ("D-", "E")
        )

        perfs = sorted(
            [(s.full_name, str(s.id), student_means[s.id]) for s in student_list],
            key=lambda x: x[2], reverse=True,
        )
        top = [
            {"student_name": name, "student_id": sid, "mean": round(mean, 2)}
            for name, sid, mean in perfs[:5]
        ]

        return ClassPerformanceSummary(
            class_id=str(class_id),
            class_name=class_name,
            term_id=str(term_id),
            total_students=len(student_list),
            subject_averages=subject_avgs,
            grade_distribution=dict(grade_dist),
            pass_rate=round((pass_count / total) * 100, 2) if total else 0.0,
            top_performers=top,
        )

    # ── Remarks generators ───────────────────────────────────────

    def _generate_teacher_remarks(self, mean: float) -> str:
        if mean >= 80:
            return "Excellent performance. Keep up the outstanding work."
        elif mean >= 65:
            return "Good performance. Continue working hard."
        elif mean >= 50:
            return "Fair performance. There is room for improvement."
        elif mean >= 35:
            return "Below average. More effort and focus required."
        else:
            return "Unsatisfactory performance. Urgent improvement needed."

    def _generate_principal_remarks(self, mean: float) -> str:
        if mean >= 70:
            return "Approved. Well done."
        elif mean >= 50:
            return "Approved. Work harder next term."
        elif mean >= 35:
            return "Promoted on probation."
        else:
            return "See the Principal."
