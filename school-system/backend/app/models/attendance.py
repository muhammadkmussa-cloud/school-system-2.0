"""School Management System — Attendance model."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class AttendanceRecord(Base, TimestampMixin):
    __tablename__ = "attendance_records"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("classes.id", ondelete="SET NULL"), nullable=False, index=True
    )
    recorded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=False
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "present" | "absent" | "late" | "excused"
    remarks: Mapped[str | None] = mapped_column(String(500))
    synced: Mapped[bool] = mapped_column(default=True)  # offline-sync flag

    # relationships
    student = relationship("Student", back_populates="attendance_records")
    class_ = relationship("Class_", back_populates="attendance_records")
    recorder = relationship("User")
