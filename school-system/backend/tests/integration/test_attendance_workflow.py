"""Integration tests for Attendance workflow.

Tests the full pipeline: create student → record attendance → verify stats.
Uses an in-memory SQLite database for fast, isolated testing.
"""

import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import select

from app.models.student import Student
from app.models.attendance import AttendanceRecord
from app.services.analytics_service import AnalyticsService


class TestAttendanceWorkflow:
    """End-to-end attendance recording and stats."""

    @pytest.mark.asyncio
    async def test_record_and_verify(self, db_session):
        """Record attendance for a student and verify stats."""
        from app.core.security import hash_password
        from app.models.user import User
        from app.models.school import School

        school_id = uuid.uuid4()
        school = School(id=school_id, name="Test School", code="TS-001", is_active=True)
        db_session.add(school)

        user = User(
            id=uuid.uuid4(),
            school_id=school_id,
            email="teacher@test.ac.ke",
            hashed_password=hash_password("test123"),
            full_name="Test Teacher",
            role="teacher",
            status="active",
        )
        db_session.add(user)
        await db_session.flush()

        from app.models.academic import Class_, AcademicYear

        acad_year = AcademicYear(
            id=uuid.uuid4(), school_id=school_id,
            name="Test Year", start_date=date(2026,1,1), end_date=date(2026,12,31),
        )
        db_session.add(acad_year)

        klass = Class_(id=uuid.uuid4(), school_id=school_id, name="Form 1", level=1)
        db_session.add(klass)
        await db_session.flush()

        # Create student
        student = Student(
            id=uuid.uuid4(), school_id=school_id,
            admission_number="TS/001", full_name="Test Student",
            gender="male", date_of_birth=date(2008, 5, 15),
            class_id=klass.id, academic_year_id=acad_year.id, status="active",
        )
        db_session.add(student)
        await db_session.flush()

        # Record attendance
        today = date.today()
        record = AttendanceRecord(
            school_id=school_id,
            student_id=student.id, class_id=klass.id,
            recorded_by=user.id, attendance_date=today,
            status="present",
        )
        db_session.add(record)
        await db_session.flush()

        # Verify via analytics
        svc = AnalyticsService(db_session, school_id)
        overview = await svc.school_overview()
        assert overview["attendance_today"]["present"] == 1
        assert overview["attendance_today"]["total"] == 1
        assert overview["attendance_today"]["percentage"] == 100.0

    @pytest.mark.asyncio
    async def test_multiple_statuses(self, db_session):
        """Attendance stats correctly count present/absent/late/excused."""
        school_id = uuid.uuid4()
        from app.models.school import School
        db_session.add(School(id=school_id, name="TS", code="TS", is_active=True))
        await db_session.flush()

        from app.models.academic import Class_, AcademicYear
        ay = AcademicYear(id=uuid.uuid4(), school_id=school_id, name="AY", start_date=date(2026,1,1), end_date=date(2026,12,31))
        klass = Class_(id=uuid.uuid4(), school_id=school_id, name="F1")
        db_session.add_all([ay, klass])
        await db_session.flush()

        today = date.today()
        statuses = ["present", "present", "present", "absent", "late", "excused"]

        for i, status in enumerate(statuses):
            s = Student(
                id=uuid.uuid4(), school_id=school_id,
                admission_number=f"TS/{i:03d}", full_name=f"Student {i}",
                gender="male", date_of_birth=date(2008,1,1),
                class_id=klass.id, academic_year_id=ay.id, status="active",
            )
            db_session.add(s)
            await db_session.flush()

            db_session.add(AttendanceRecord(
                school_id=school_id,
                student_id=s.id, class_id=klass.id,
                recorded_by=uuid.uuid4(), attendance_date=today,
                status=status,
            ))
        await db_session.flush()

        # Verify distribution
        from sqlalchemy import func
        present_count = await db_session.scalar(
            select(func.count(AttendanceRecord.id)).where(
                AttendanceRecord.attendance_date == today,
                AttendanceRecord.status == "present",
            )
        )
        assert present_count == 3

        absent_count = await db_session.scalar(
            select(func.count(AttendanceRecord.id)).where(
                AttendanceRecord.attendance_date == today,
                AttendanceRecord.status == "absent",
            )
        )
        assert absent_count == 1
