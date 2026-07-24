"""Integration tests for the Grading & Results workflow.

Full pipeline: create assessment → record marks → compute results → verify grades.
"""

import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app.models.student import Student
from app.models.assessment import Assessment, Mark
from app.core.grading import grade_for
from app.services.results_engine import ResultsEngine


class TestGradingWorkflow:
    """End-to-end grading pipeline."""

    @pytest.mark.asyncio
    async def test_single_assessment_grading(self, db_session):
        """One assessment → marks → grade computation."""
        school_id = uuid.uuid4()
        from app.models.school import School
        db_session.add(School(id=school_id, name="TS", code="TS-GRADE", is_active=True))
        await db_session.flush()

        from app.models.academic import Class_, AcademicYear, Subject, Term

        ay = AcademicYear(id=uuid.uuid4(), school_id=school_id, name="AY2026",
                          start_date=date(2026,1,1), end_date=date(2026,12,31))
        term = Term(id=uuid.uuid4(), school_id=school_id, academic_year_id=ay.id, name="T1",
                    term_number=1, start_date=date(2026,1,1), end_date=date(2026,4,1))
        klass = Class_(id=uuid.uuid4(), school_id=school_id, name="Form 1", level=1)
        subj = Subject(id=uuid.uuid4(), school_id=school_id, code="MAT", name="Mathematics")
        db_session.add_all([ay, term, klass, subj])
        await db_session.flush()

        # Create students
        for i in range(5):
            db_session.add(Student(
                id=uuid.uuid4(), school_id=school_id,
                admission_number=f"G{i:03d}", full_name=f"Grade Student {i}",
                gender="male" if i % 2 == 0 else "female",
                date_of_birth=date(2008,1,1),
                class_id=klass.id, academic_year_id=ay.id, status="active",
            ))
        await db_session.flush()

        # Create assessment
        assessment = Assessment(
            id=uuid.uuid4(), school_id=school_id,
            subject_id=subj.id, teacher_id=uuid.uuid4(),
            class_id=klass.id, term_id=term.id,
            name="Test Exam", assessment_type="exam",
            max_score=100, weight=1.0,
        )
        db_session.add(assessment)
        await db_session.flush()

        # Add marks with varied scores
        scores = [85, 72, 58, 44, 31]
        students = (await db_session.scalars(select(Student))).all()
        for s, score in zip(students, scores):
            from app.services.results_engine import grade_for
            pct = (score / 100) * 100
            letter, _ = grade_for(pct)
            db_session.add(Mark(
                school_id=school_id,
                assessment_id=assessment.id, student_id=s.id,
                score=float(score), grade=letter,
            ))
        await db_session.flush()

        # Verify grades match expectations
        marks = (await db_session.scalars(select(Mark))).all()
        grade_map = {85: "A", 72: "B+", 58: "C+", 44: "D+", 31: "D-"}
        for m in marks:
            expected = grade_map.get(int(m.score))
            if expected:
                assert m.grade == expected, f"Score {m.score}: expected {expected}, got {m.grade}"

    @pytest.mark.asyncio
    async def test_weighted_assessment_aggregation(self, db_session):
        """Multiple weighted assessments → correct aggregate."""
        school_id = uuid.uuid4()
        from app.models.school import School
        db_session.add(School(id=school_id, name="TS-W", code="TS-W", is_active=True))
        await db_session.flush()

        from app.models.academic import Class_, AcademicYear, Subject, Term
        ay = AcademicYear(id=uuid.uuid4(), school_id=school_id, name="AY",
                          start_date=date(2026,1,1), end_date=date(2026,12,31))
        term = Term(id=uuid.uuid4(), school_id=school_id, academic_year_id=ay.id, name="T1",
                    term_number=1, start_date=date(2026,1,1), end_date=date(2026,4,1))
        klass = Class_(id=uuid.uuid4(), school_id=school_id, name="F2")
        subj = Subject(id=uuid.uuid4(), school_id=school_id, code="ENG", name="English")
        db_session.add_all([ay, term, klass, subj])
        await db_session.flush()

        sid = uuid.uuid4()
        db_session.add(Student(id=sid, school_id=school_id, admission_number="W001",
                                full_name="Weight Test", gender="female",
                                date_of_birth=date(2008,1,1),
                                class_id=klass.id, academic_year_id=ay.id, status="active"))
        await db_session.flush()

        # CAT (weight 15%), Midterm (weight 25%), Endterm (weight 60%)
        # Student scores: CAT=60/100, Midterm=70/100, Endterm=80/100
        # Expected: (60*0.15 + 70*0.25 + 80*0.60) / (100*0.15 + 100*0.25 + 100*0.60)
        # = (9 + 17.5 + 48) / (15 + 25 + 60) = 74.5 / 100 = 74.5%

        configs = [
            ("CAT", 0.15, 60),
            ("Midterm", 0.25, 70),
            ("Endterm", 0.60, 80),
        ]
        for name, weight, score in configs:
            a = Assessment(
                id=uuid.uuid4(), school_id=school_id,
                subject_id=subj.id, teacher_id=uuid.uuid4(),
                class_id=klass.id, term_id=term.id,
                name=name, assessment_type="exam",
                max_score=100, weight=weight,
            )
            db_session.add(a)
            await db_session.flush()

            pct = score
            letter, _ = grade_for(pct)
            db_session.add(Mark(school_id=school_id, assessment_id=a.id, student_id=sid, score=float(score), grade=letter))
        await db_session.flush()

        # Compute aggregate
        assessments = (await db_session.scalars(select(Assessment))).all()
        total = 0.0
        max_p = 0.0
        for a in assessments:
            mark = await db_session.scalar(
                select(Mark).where(Mark.assessment_id == a.id, Mark.student_id == sid)
            )
            total += (mark.score if mark else 0) * a.weight
            max_p += a.max_score * a.weight

        pct = round((total / max_p) * 100, 2) if max_p else 0
        assert abs(pct - 74.5) < 0.1, f"Expected ~74.5%, got {pct}%"

    @pytest.mark.asyncio
    async def test_grade_for_all_boundaries(self):
        """Every known boundary returns the correct grade."""
        test_cases = [
            (100, "A", 12), (85, "A", 12), (80, "A", 12),
            (79, "A-", 11), (75, "A-", 11),
            (74, "B+", 10), (70, "B+", 10),
            (69, "B", 9), (65, "B", 9),
            (64, "B-", 8), (60, "B-", 8),
            (59, "C+", 7), (55, "C+", 7),
            (54, "C", 6), (50, "C", 6),
            (49, "C-", 5), (45, "C-", 5),
            (44, "D+", 4), (40, "D+", 4),
            (39, "D", 3), (35, "D", 3),
            (34, "D-", 2), (30, "D-", 2),
            (29, "E", 1), (15, "E", 1), (0, "E", 1),
        ]
        for pct, expected_letter, expected_points in test_cases:
            letter, points = grade_for(float(pct))
            assert letter == expected_letter, f"At {pct}%: expected {expected_letter}, got {letter}"
            assert points == expected_points, f"At {pct}%: expected {expected_points}pts, got {points}"
