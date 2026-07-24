"""Timetable schemas."""

from __future__ import annotations

import uuid
from datetime import datetime, time

from pydantic import BaseModel, Field, model_validator


class TimetableEntryCreate(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    subject_id: uuid.UUID
    teacher_id: uuid.UUID
    class_id: uuid.UUID
    room: str | None = None


class TimetableEntryOut(BaseModel):
    id: uuid.UUID
    day_of_week: int
    start_time: time
    end_time: time
    subject_id: uuid.UUID
    teacher_id: uuid.UUID
    class_id: uuid.UUID
    room: str | None = None
    model_config = {"from_attributes": True}


class TimetableCreate(BaseModel):
    academic_year_id: uuid.UUID
    name: str
    entries: list[TimetableEntryCreate] = []


class TimetableOut(BaseModel):
    id: uuid.UUID
    name: str
    academic_year_id: uuid.UUID
    is_active: bool
    entries: list[TimetableEntryOut] = []
    created_at: datetime
    model_config = {"from_attributes": True}


class ConflictCheck(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    teacher_id: uuid.UUID | None = None
    class_id: uuid.UUID | None = None
    room: str | None = None
