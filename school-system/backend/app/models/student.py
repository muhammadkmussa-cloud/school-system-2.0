"""School Management System — Student model."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Student(Base, TimestampMixin):
    __tablename__ = "students"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    admission_number: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    gender: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # "male" | "female" | "other"
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.id", ondelete="SET NULL"), nullable=False
    )
    stream_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("streams.id", ondelete="SET NULL")
    )
    academic_year_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False
    )
    parent_name: Mapped[str | None] = mapped_column(String(200))
    parent_phone: Mapped[str | None] = mapped_column(String(30))
    parent_email: Mapped[str | None] = mapped_column(String(255))
    medical_notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), default="active", nullable=False
    )  # "active" | "archived" | "transferred" | "graduated"

    # unique constraint per school
    __table_args__ = (
        UniqueConstraint("school_id", "admission_number", name="uq_school_admission"),
    )

    # relationships
    school = relationship("School", back_populates="students")
    class_ = relationship("Class_", back_populates="students", foreign_keys=[class_id])
    stream = relationship("Stream", back_populates="students")
    academic_year = relationship("AcademicYear", back_populates="students")
    attendance_records = relationship(
        "AttendanceRecord", back_populates="student", lazy="dynamic"
    )
    marks = relationship("Mark", back_populates="student", lazy="dynamic")
