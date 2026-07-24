"""Lesson Plan schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class LessonCreate(BaseModel):
    subject_id: uuid.UUID
    class_id: uuid.UUID
    topic: str
    objectives: str | None = None
    activities: str | None = None
    teaching_resources: str | None = None
    assessment: str | None = None
    homework: str | None = None
    week_number: int | None = Field(default=None, ge=1)
    term_number: int | None = Field(default=None, ge=1)


class LessonUpdate(BaseModel):
    subject_id: uuid.UUID | None = None
    class_id: uuid.UUID | None = None
    topic: str | None = None
    objectives: str | None = None
    activities: str | None = None
    teaching_resources: str | None = None
    assessment: str | None = None
    homework: str | None = None
    completion_status: str | None = None
    week_number: int | None = Field(default=None, ge=1)
    term_number: int | None = Field(default=None, ge=1)


class LessonDuplicate(BaseModel):
    source_plan_id: uuid.UUID
    class_id: uuid.UUID | None = None
    subject_id: uuid.UUID | None = None


class LessonOut(BaseModel):
    id: uuid.UUID
    teacher_id: uuid.UUID
    subject_id: uuid.UUID
    class_id: uuid.UUID
    topic: str
    objectives: str | None = None
    activities: str | None = None
    teaching_resources: str | None = None
    assessment: str | None = None
    homework: str | None = None
    completion_status: str
    week_number: int | None = None
    term_number: int | None = None
    source_plan_id: uuid.UUID | None = None
    created_at: datetime
    model_config = {"from_attributes": True}
