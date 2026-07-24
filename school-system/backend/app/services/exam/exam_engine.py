"""School Management System — Exam Engine.

Aggregates exam scores across:
- Multiple papers per subject (weighted)
- Multiple series per term (weighted)
- Configurable grade boundaries per school
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exam import ExamSeries, ExamPaper, ExamScore
from app.models.student import Student
from app.core.grading import compute_term_mean, grade_for

# ── Default weighting configuration ─────────────────────────────────

DEFAULT_SERIES_WEIGHTS = {
    "cat": 15.0,       # Continuous Assessment Tests
    "midterm": 25.0,   # Mid-Term Exams
    "endterm": 40.0,   # End of Term Exams
    "practical": 10.0, # Practical Exams
    "project": 10.0,   # Projects
    "mock": 100.0,     # Mock (standalone — full 100%)
}


@dataclass
class ExamSubjectResult:
    subject_id: str
    subject_name: str
    total: float
    max_possible: float
    percentage: float
    grade: str
    points: int
    paper_scores: list[dict] = field(default_factory=list)


@dataclass
class ExamTermReport:
    student_id: str
    student_name: str
    admission_number: str
    class_id: str
    term_id: str
    subjects: list[ExamSubjectResult] = field(default_factory=list)
    overall_mean: float = 0.0
    overall_grade: str = ""
    overall_points: int = 0
    rank: int = 0
    total_subjects: int = 0


class ExamEngine:
    """Aggregates exam scores across series → papers → subjects → overall."""

    def __init__(self, db: AsyncSession, school_id: uuid.UUID):
        self.db = db
        self.school_id = school_id

    async def compute_term_results(
        self, student_id: uuid.UUID, term_id: uuid.UUID
    ) -> ExamTermReport | None:
        """Full term results for one student across all exam series & papers."""

        student = await self.db.scalar(
            select(Student).where(
                Student.id == student_id,
                Student.school_id == self.school_id,
            )
        )
        if not student:
            return None

        # All exam series in this term
        series_list = await self.db.scalars(
            select(ExamSeries).where(
                ExamSeries.school_id == self.school_id,
                ExamSeries.term_id == term_id,
            )
        )
        series_items = list(series_list)

        # All papers for all series
        all_papers: list[ExamPaper] = []
        for s in series_items:
            papers = await self.db.scalars(
                select(ExamPaper).where(ExamPaper.series_id == s.id)
            )
            all_papers.extend(papers)

        # Group papers by subject
        papers_by_subject: dict[uuid.UUID, list[tuple[ExamPaper, float]]] = defaultdict(list)
        # (paper, series_weight)
        series_weight_map: dict[uuid.UUID, float] = {}
        for s in series_items:
            w = DEFAULT_SERIES_WEIGHTS.get(s.series_type, 30.0)
            if abs(s.weight_percentage - 30.0) > 0.01:  # overridden
                w = s.weight_percentage
            series_weight_map[s.id] = w

        for p in all_papers:
            if p.class_id != student.class_id:
                continue
            sw = series_weight_map.get(p.series_id, 30.0)
            papers_by_subject[p.subject_id].append((p, sw))

        # Load subject names
        from app.models.academic import Subject
        subj_ids = list(papers_by_subject.keys())
        subj_names: dict[uuid.UUID, str] = {}
        if subj_ids:
            subs = await self.db.scalars(select(Subject).where(Subject.id.in_(subj_ids)))
            for s in subs:
                subj_names[s.id] = s.name

        # Compute per subject
        subject_results: list[ExamSubjectResult] = []
        total_pct_sum = 0.0
        total_pts = 0

        for subj_id, paper_entries in papers_by_subject.items():
            # Normalize weights within the subject (papers weighted, then scaled by series weight)
            subj_total = 0.0
            subj_max = 0.0
            paper_details = []

            for paper, series_weight in paper_entries:
                score_row = await self.db.scalar(
                    select(ExamScore).where(
                        ExamScore.paper_id == paper.id,
                        ExamScore.student_id == student_id,
                    )
                )
                raw_score = score_row.score if score_row and not score_row.is_absent else 0.0
                weighted_score = raw_score * paper.weight * (series_weight / 100.0)
                weighted_max = paper.max_score * paper.weight * (series_weight / 100.0)
                subj_total += weighted_score
                subj_max += weighted_max
                paper_details.append({
                    "paper": paper.name,
                    "code": paper.paper_code,
                    "score": raw_score,
                    "max": paper.max_score,
                    "weight": paper.weight,
                    "series_weight": series_weight,
                })

            pct = (subj_total / subj_max * 100) if subj_max > 0 else 0.0
            letter, pts = grade_for(pct)
            total_pct_sum += pct
            total_pts += pts

            subject_results.append(ExamSubjectResult(
                subject_id=str(subj_id),
                subject_name=subj_names.get(subj_id, "Unknown"),
                total=round(subj_total, 2),
                max_possible=round(subj_max, 2),
                percentage=round(pct, 2),
                grade=letter,
                points=pts,
                paper_scores=paper_details,
            ))

        overall_mean = compute_term_mean(total_pct_sum, len(subject_results))
        overall_grade, overall_points = grade_for(overall_mean)

        return ExamTermReport(
            student_id=str(student.id),
            student_name=student.full_name,
            admission_number=student.admission_number,
            class_id=str(student.class_id),
            term_id=str(term_id),
            subjects=subject_results,
            overall_mean=overall_mean,
            overall_grade=overall_grade,
            overall_points=overall_points,
            total_subjects=n,
        )

    async def class_exam_ranking(
        self, class_id: uuid.UUID, term_id: uuid.UUID
    ) -> list[dict]:
        """Rank all students in a class by exam performance."""

        students = await self.db.scalars(
            select(Student).where(
                Student.class_id == class_id,
                Student.school_id == self.school_id,
                Student.status == "active",
            )
        )
        rankings = []
        for st in students:
            report = await self.compute_term_results(st.id, term_id)
            if report:
                rankings.append({
                    "student_id": str(st.id),
                    "name": st.full_name,
                    "admission_number": st.admission_number,
                    "mean": report.overall_mean,
                    "grade": report.overall_grade,
                    "points": report.overall_points,
                })

        rankings.sort(key=lambda x: x["mean"], reverse=True)
        for i, r in enumerate(rankings):
            r["rank"] = i + 1

        return rankings
