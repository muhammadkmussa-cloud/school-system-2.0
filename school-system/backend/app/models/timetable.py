"""School Management System — Timetable models."""

from __future__ import annotations

import uuid
from datetime import time

from sqlalchemy import ForeignKey, String, Time
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Timetable(Base, TimestampMixin):
    __tablename__ = "timetables"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("academic_years.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)

    school = relationship("School", back_populates="timetables")
    academic_year = relationship("AcademicYear", back_populates="timetables")
    entries = relationship(
        "TimetableEntry", back_populates="timetable", lazy="dynamic", cascade="all, delete-orphan"
    )


class TimetableEntry(Base, TimestampMixin):
    __tablename__ = "timetable_entries"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timetable_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("timetables.id", ondelete="CASCADE"),
        nullable=False,
    )
    day_of_week: Mapped[int] = mapped_column(nullable=False)  # 0=Mon … 6=Sun
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False
    )
    room: Mapped[str | None] = mapped_column(String(100))

    timetable = relationship("Timetable", back_populates="entries")
    subject = relationship("Subject", back_populates="timetable_entries")
    teacher = relationship("Teacher", back_populates="timetable_entries")
    class_ = relationship("Class_", back_populates="timetable_entries")
