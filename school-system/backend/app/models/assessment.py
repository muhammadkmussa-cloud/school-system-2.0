"""School Management System — Assessment & Mark models."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Assessment(Base, TimestampMixin):
    __tablename__ = "assessments"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teachers.id", ondelete="SET NULL"), nullable=False, index=True
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    term_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("terms.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    assessment_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "exam" | "test" | "quiz" | "assignment" | "project"
    max_score: Mapped[float] = mapped_column(Float, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    date_administered: Mapped[date | None] = mapped_column()
    description: Mapped[str | None] = mapped_column(Text)

    school = relationship("School", back_populates="assessments")
    subject = relationship("Subject", back_populates="assessments")
    teacher = relationship("Teacher", back_populates="assessments")
    term = relationship("Term", back_populates="assessments")
    marks = relationship("Mark", back_populates="assessment", lazy="dynamic", cascade="all, delete-orphan")


class Mark(Base, TimestampMixin):
    __tablename__ = "marks"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    grade: Mapped[str | None] = mapped_column(String(5))  # A, A-, B+ etc.
    remarks: Mapped[str | None] = mapped_column(String(500))
    synced: Mapped[bool] = mapped_column(default=True)

    assessment = relationship("Assessment", back_populates="marks")
    student = relationship("Student", back_populates="marks")
