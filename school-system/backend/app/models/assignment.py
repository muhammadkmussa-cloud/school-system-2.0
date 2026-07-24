"""School Management System — Digital Assignment Models.

Homework and assignment management with submission tracking.
Teachers create assignments; students submit (future: student portal).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Assignment(Base, TimestampMixin):
    """A homework or class assignment created by a teacher."""
    __tablename__ = "assignments"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teachers.id", ondelete="SET NULL"), nullable=False
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    assignment_type: Mapped[str] = mapped_column(
        String(30), default="homework"
    )  # "homework", "classwork", "project", "takeaway"

    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_score: Mapped[float | None] = mapped_column(Float)

    # Attachments (future: S3 URLs)
    attachment_urls: Mapped[str | None] = mapped_column(Text)

    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_late_submission: Mapped[bool] = mapped_column(Boolean, default=True)

    submissions = relationship("AssignmentSubmission", back_populates="assignment",
                               lazy="dynamic", cascade="all, delete-orphan")


class AssignmentSubmission(Base, TimestampMixin):
    """A student's submission for an assignment."""
    __tablename__ = "assignment_submissions"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_late: Mapped[bool] = mapped_column(Boolean, default=False)

    # Content
    content: Mapped[str | None] = mapped_column(Text)  # text response
    attachment_url: Mapped[str | None] = mapped_column(String(500))

    # Grading
    score: Mapped[float | None] = mapped_column(Float)
    grade: Mapped[str | None] = mapped_column(String(5))
    teacher_comment: Mapped[str | None] = mapped_column(Text)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    graded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    assignment = relationship("Assignment", back_populates="submissions")
