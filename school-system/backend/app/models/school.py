"""School Management System — School model (multi-tenancy root)."""

from __future__ import annotations

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class School(Base, TimestampMixin):
    __tablename__ = "schools"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, index=True
    )
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(Text)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    subscription_tier: Mapped[str] = mapped_column(
        String(50), default="free", nullable=False
    )
    subscription_expires_at: Mapped[str | None] = mapped_column(String(50))

    # relationships
    users = relationship("User", back_populates="school", lazy="dynamic")
    teachers = relationship("Teacher", back_populates="school", lazy="dynamic")
    students = relationship("Student", back_populates="school", lazy="dynamic")
    academic_years = relationship("AcademicYear", back_populates="school", lazy="dynamic")
    classes = relationship("Class_", back_populates="school", lazy="dynamic")
    streams = relationship("Stream", back_populates="school", lazy="dynamic")
    subjects = relationship("Subject", back_populates="school", lazy="dynamic")
    departments = relationship("Department", back_populates="school", lazy="dynamic")
    timetables = relationship("Timetable", back_populates="school", lazy="dynamic")
    assessments = relationship("Assessment", back_populates="school", lazy="dynamic")
    lesson_plans = relationship("LessonPlan", back_populates="school", lazy="dynamic")
