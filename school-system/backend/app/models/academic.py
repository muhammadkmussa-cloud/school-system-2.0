"""School Management System — Academic Structure models."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Boolean, Date, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class AcademicYear(Base, TimestampMixin):
    __tablename__ = "academic_years"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)

    school = relationship("School", back_populates="academic_years")
    terms = relationship("Term", back_populates="academic_year", lazy="dynamic")
    students = relationship("Student", back_populates="academic_year", lazy="dynamic")
    timetables = relationship("Timetable", back_populates="academic_year", lazy="dynamic")


class Term(Base, TimestampMixin):
    __tablename__ = "terms"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_years.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    term_number: Mapped[int] = mapped_column(nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)

    academic_year = relationship("AcademicYear", back_populates="terms")
    assessments = relationship("Assessment", back_populates="term", lazy="dynamic")


class Class_(Base, TimestampMixin):
    __tablename__ = "classes"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[int] = mapped_column(nullable=True)  # numeric level e.g. 1 for Form 1
    description: Mapped[str | None] = mapped_column(String(500))

    school = relationship("School", back_populates="classes")
    students = relationship(
        "Student",
        back_populates="class_",
        lazy="dynamic",
        foreign_keys="Student.class_id",
    )
    streams = relationship("Stream", back_populates="class_", lazy="dynamic")
    timetable_entries = relationship(
        "TimetableEntry", back_populates="class_", lazy="dynamic"
    )
    attendance_records = relationship(
        "AttendanceRecord", back_populates="class_", lazy="dynamic"
    )


class Stream(Base, TimestampMixin):
    __tablename__ = "streams"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    school = relationship("School", back_populates="streams")
    class_ = relationship("Class_", back_populates="streams")
    students = relationship("Student", back_populates="stream", lazy="dynamic")


class Subject(Base, TimestampMixin):
    __tablename__ = "subjects"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL")
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))

    school = relationship("School", back_populates="subjects")
    department = relationship("Department", back_populates="subjects")
    timetable_entries = relationship(
        "TimetableEntry", back_populates="subject", lazy="dynamic"
    )
    assessments = relationship("Assessment", back_populates="subject", lazy="dynamic")
    lesson_plans = relationship("LessonPlan", back_populates="subject", lazy="dynamic")


class Department(Base, TimestampMixin):
    __tablename__ = "departments"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))

    school = relationship("School", back_populates="departments")
    subjects = relationship("Subject", back_populates="department", lazy="dynamic")
