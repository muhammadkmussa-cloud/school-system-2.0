"""School Management System — Exam & Assessment Configuration models.

Supports full exam hierarchy:
    Exam Series → Exam Papers → Weighted Components

Example: "Term 1 End of Term Exam" → Maths Paper 1, Paper 2, Practical
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, String, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class ExamSeries(Base, TimestampMixin):
    """A coordinated set of exams (e.g., "Term 1 End-Term Exams 2026")."""
    __tablename__ = "exam_series"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    term_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("terms.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    series_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # "cat", "midterm", "endterm", "practical", "project", "mock"
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    weight_percentage: Mapped[float] = mapped_column(
        Float, default=30.0
    )  # Contribution to term grade

    exam_papers = relationship("ExamPaper", back_populates="series", lazy="dynamic", cascade="all, delete-orphan")


class ExamPaper(Base, TimestampMixin):
    """An individual exam paper within a series (e.g., "Mathematics Paper 1")."""
    __tablename__ = "exam_papers"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    series_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exam_series.id", ondelete="CASCADE"), nullable=False
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    paper_code: Mapped[str | None] = mapped_column(String(20))  # e.g., "P1", "P2", "PRAC"
    max_score: Mapped[float] = mapped_column(Float, nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    duration_minutes: Mapped[int | None] = mapped_column()
    exam_date: Mapped[date | None] = mapped_column(Date)
    instructions: Mapped[str | None] = mapped_column(Text)

    series = relationship("ExamSeries", back_populates="exam_papers")
    scores = relationship("ExamScore", back_populates="paper", lazy="dynamic", cascade="all, delete-orphan")


class ExamScore(Base, TimestampMixin):
    """A single student's score on a specific exam paper."""
    __tablename__ = "exam_scores"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    paper_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("exam_papers.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    grade: Mapped[str | None] = mapped_column(String(5))
    is_absent: Mapped[bool] = mapped_column(Boolean, default=False)
    remarks: Mapped[str | None] = mapped_column(String(500))

    paper = relationship("ExamPaper", back_populates="scores")
