"""Gradebook / Assessment schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class MarkEntry(BaseModel):
    student_id: uuid.UUID
    score: float = Field(ge=0)
    remarks: str | None = None


class AssessmentCreate(BaseModel):
    subject_id: uuid.UUID
    class_id: uuid.UUID
    term_id: uuid.UUID | None = None
    name: str
    assessment_type: str = Field(..., pattern=r"^(exam|test|quiz|assignment|project)$")
    max_score: float = Field(gt=0)
    weight: float = Field(default=1.0, ge=0)
    date_administered: date | None = None
    description: str | None = None


class AssessmentOut(BaseModel):
    id: uuid.UUID
    subject_id: uuid.UUID
    teacher_id: uuid.UUID
    class_id: uuid.UUID
    term_id: uuid.UUID | None = None
    name: str
    assessment_type: str
    max_score: float
    weight: float
    date_administered: date | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class MarkOut(BaseModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    student_id: uuid.UUID
    score: float
    grade: str | None = None
    remarks: str | None = None
    synced: bool
    model_config = {"from_attributes": True}


class AssessmentStats(BaseModel):
    assessment_id: uuid.UUID
    total_students: int
    average: float
    highest: float
    lowest: float
    class_average: float
    grade_distribution: dict[str, int]


class StudentGrade(BaseModel):
    student_id: uuid.UUID
    student_name: str
    total: float
    percentage: float = Field(ge=0, le=100)
    grade: str
