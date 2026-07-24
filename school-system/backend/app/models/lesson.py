"""School Management System — Lesson Plan model."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class LessonPlan(Base, TimestampMixin):
    __tablename__ = "lesson_plans"

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
    topic: Mapped[str] = mapped_column(String(300), nullable=False)
    objectives: Mapped[str | None] = mapped_column(Text)
    activities: Mapped[str | None] = mapped_column(Text)
    teaching_resources: Mapped[str | None] = mapped_column(Text)
    assessment: Mapped[str | None] = mapped_column(Text)  # how to assess understanding
    homework: Mapped[str | None] = mapped_column(Text)
    completion_status: Mapped[str] = mapped_column(
        String(30), default="planned"
    )  # "planned" | "in_progress" | "completed"
    week_number: Mapped[int | None] = mapped_column()
    term_number: Mapped[int | None] = mapped_column()
    source_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True)
    )  # tracks duplication

    school = relationship("School", back_populates="lesson_plans")
    teacher = relationship("Teacher", back_populates="lesson_plans")
    subject = relationship("Subject", back_populates="lesson_plans")
