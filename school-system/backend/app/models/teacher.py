"""School Management System — Teacher profile model."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Teacher(Base, TimestampMixin):
    __tablename__ = "teachers"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    employee_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    is_active: Mapped[bool] = mapped_column(default=True)

    # relationships
    school = relationship("School", back_populates="teachers")
    user = relationship("User", back_populates="teacher_profile")
    timetable_entries = relationship(
        "TimetableEntry", back_populates="teacher", lazy="dynamic"
    )
    assessments = relationship("Assessment", back_populates="teacher", lazy="dynamic")
    lesson_plans = relationship("LessonPlan", back_populates="teacher", lazy="dynamic")
