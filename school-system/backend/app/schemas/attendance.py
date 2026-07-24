"""Attendance schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class AttendanceEntry(BaseModel):
    student_id: uuid.UUID
    status: str = Field(..., pattern=r"^(present|absent|late|excused)$")
    remarks: str | None = None


class AttendanceBatchCreate(BaseModel):
    class_id: uuid.UUID
    attendance_date: date
    records: list[AttendanceEntry]


class AttendanceOut(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    class_id: uuid.UUID
    recorded_by: uuid.UUID
    attendance_date: date
    status: str
    remarks: str | None = None
    synced: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class AttendanceStats(BaseModel):
    total_students: int
    present: int
    absent: int
    late: int
    excused: int
    percentage: float = Field(ge=0, le=100)


class AttendanceHistory(BaseModel):
    records: list[AttendanceOut]
    stats: AttendanceStats
