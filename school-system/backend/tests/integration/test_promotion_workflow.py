"""Integration tests for Student Promotion workflow.

Tests: bulk promote, retain below min_mean, graduation, rollback.
"""

import uuid
from datetime import date

import pytest
from sqlalchemy import select

from app.models.student import Student
from app.services.promotion_service import PromotionService


class TestPromotionWorkflow:
    """End-to-end promotion pipeline."""

    @pytest.mark.asyncio
    async def test_bulk_promote_all(self, db_session):
        """Promote all students from one class to the next."""
        school_id = uuid.uuid4()
        from app.models.school import School
        db_session.add(School(id=school_id, name="Promo School", code="PS", is_active=True))
        await db_session.flush()

        from app.models.academic import Class_, AcademicYear

        ay1 = AcademicYear(id=uuid.uuid4(), school_id=school_id, name="2025",
                           start_date=date(2025,1,1), end_date=date(2025,12,31))
        ay2 = AcademicYear(id=uuid.uuid4(), school_id=school_id, name="2026",
                           start_date=date(2026,1,1), end_date=date(2026,12,31))
        f1 = Class_(id=uuid.uuid4(), school_id=school_id, name="Form 1", level=1)
        f2 = Class_(id=uuid.uuid4(), school_id=school_id, name="Form 2", level=2)
        db_session.add_all([ay1, ay2, f1, f2])
        await db_session.flush()

        # Create 10 students in Form 1
        for i in range(10):
            db_session.add(Student(
                id=uuid.uuid4(), school_id=school_id,
                admission_number=f"P{i:03d}", full_name=f"Promo Student {i}",
                gender="male" if i % 2 == 0 else "female",
                date_of_birth=date(2008,1,1),
                class_id=f1.id, academic_year_id=ay1.id, status="active",
            ))
        await db_session.flush()

        svc = PromotionService(db_session, school_id)
        result = await svc.promote_class(
            source_class_id=f1.id,
            target_class_id=f2.id,
            target_academic_year_id=ay2.id,
        )

        assert result.promoted == 10
        assert result.retained == 0
        assert result.graduated == 0

        # Verify all moved to Form 2
        students = (await db_session.scalars(
            select(Student).where(Student.school_id == school_id, Student.status == "active")
        )).all()
        for s in students:
            assert s.class_id == f2.id
            assert s.academic_year_id == ay2.id

    @pytest.mark.asyncio
    async def test_promote_with_retain_min_mean(self, db_session):
        """Students below min_mean are retained."""
        school_id = uuid.uuid4()
        from app.models.school import School
        db_session.add(School(id=school_id, name="RS", code="RS", is_active=True))
        await db_session.flush()

        from app.models.academic import Class_, AcademicYear, Term

        ay1 = AcademicYear(id=uuid.uuid4(), school_id=school_id, name="2025",
                           start_date=date(2025,1,1), end_date=date(2025,12,31))
        ay2 = AcademicYear(id=uuid.uuid4(), school_id=school_id, name="2026",
                           start_date=date(2026,1,1), end_date=date(2026,12,31))
        f1 = Class_(id=uuid.uuid4(), school_id=school_id, name="Form 1", level=1)
        f2 = Class_(id=uuid.uuid4(), school_id=school_id, name="Form 2", level=2)
        term = Term(id=uuid.uuid4(), school_id=school_id, academic_year_id=ay1.id, name="T1",
                    term_number=1, start_date=date(2025,1,1), end_date=date(2025,4,1), is_current=True)
        db_session.add_all([ay1, ay2, f1, f2, term])
        await db_session.flush()

        # Create students
        for i in range(5):
            db_session.add(Student(
                id=uuid.uuid4(), school_id=school_id,
                admission_number=f"R{i:03d}", full_name=f"Retain Student {i}",
                gender="male", date_of_birth=date(2008,1,1),
                class_id=f1.id, academic_year_id=ay1.id, status="active",
            ))
        await db_session.flush()

        svc = PromotionService(db_session, school_id)

        # Without marks, all students have mean=0, so min_mean=35 retains everyone
        result = await svc.promote_class(
            source_class_id=f1.id,
            target_class_id=f2.id,
            target_academic_year_id=ay2.id,
            min_mean=35.0,
            term_id=term.id,
        )

        # All should be retained since they have no marks (mean=0 < 35)
        assert result.retained == 5
        assert result.promoted == 0

    @pytest.mark.asyncio
    async def test_graduation(self, db_session):
        """Students in highest level are graduated, not promoted."""
        school_id = uuid.uuid4()
        from app.models.school import School
        db_session.add(School(id=school_id, name="GS", code="GS", is_active=True))
        await db_session.flush()

        from app.models.academic import Class_, AcademicYear

        ay1 = AcademicYear(id=uuid.uuid4(), school_id=school_id, name="2025",
                           start_date=date(2025,1,1), end_date=date(2025,12,31))
        ay2 = AcademicYear(id=uuid.uuid4(), school_id=school_id, name="2026",
                           start_date=date(2026,1,1), end_date=date(2026,12,31))
        f4 = Class_(id=uuid.uuid4(), school_id=school_id, name="Form 4", level=4)
        f5 = Class_(id=uuid.uuid4(), school_id=school_id, name="Form 5", level=5)
        db_session.add_all([ay1, ay2, f4, f5])
        await db_session.flush()

        # Level 5 also graduates (>=4 is graduating)
        for i in range(3):
            db_session.add(Student(
                id=uuid.uuid4(), school_id=school_id,
                admission_number=f"G{i:03d}", full_name=f"Grad Student {i}",
                gender="male", date_of_birth=date(2006,1,1),
                class_id=f4.id, academic_year_id=ay1.id, status="active",
            ))
        await db_session.flush()

        svc = PromotionService(db_session, school_id)
        result = await svc.promote_class(
            source_class_id=f4.id,
            target_class_id=f5.id,
            target_academic_year_id=ay2.id,
        )

        assert result.graduated == 3
        assert result.promoted == 0

        # Verify graduated status
        students = (await db_session.scalars(
            select(Student).where(Student.school_id == school_id)
        )).all()
        for s in students:
            assert s.status == "graduated"

    @pytest.mark.asyncio
    async def test_rollback(self, db_session):
        """Rollback undoes a promotion."""
        school_id = uuid.uuid4()
        from app.models.school import School
        db_session.add(School(id=school_id, name="RB", code="RB", is_active=True))
        await db_session.flush()

        from app.models.academic import Class_, AcademicYear
        ay1 = AcademicYear(id=uuid.uuid4(), school_id=school_id, name="2025",
                           start_date=date(2025,1,1), end_date=date(2025,12,31))
        ay2 = AcademicYear(id=uuid.uuid4(), school_id=school_id, name="2026",
                           start_date=date(2026,1,1), end_date=date(2026,12,31))
        f1 = Class_(id=uuid.uuid4(), school_id=school_id, name="Form 1", level=1)
        f2 = Class_(id=uuid.uuid4(), school_id=school_id, name="Form 2", level=2)
        db_session.add_all([ay1, ay2, f1, f2])
        await db_session.flush()

        sid = uuid.uuid4()
        db_session.add(Student(id=sid, school_id=school_id, admission_number="RB001",
                                full_name="Rollback Student", gender="male",
                                date_of_birth=date(2008,1,1),
                                class_id=f1.id, academic_year_id=ay1.id, status="active"))
        await db_session.flush()

        svc = PromotionService(db_session, school_id)

        # Promote
        result = await svc.promote_class(f1.id, f2.id, ay2.id)
        assert result.promoted == 1

        # Verify moved
        student = await db_session.scalar(select(Student).where(Student.id == sid))
        assert student.class_id == f2.id

        # Rollback
        rollback_result = await svc.rollback()
        assert rollback_result.promoted == 1

        # Verify restored
        await db_session.refresh(student)
        assert student.class_id == f1.id
        assert student.status == "active"
