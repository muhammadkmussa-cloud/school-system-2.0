"""Exam, paper, and score schemas."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, Field


class ExamSeriesCreate(BaseModel):
    term_id: uuid.UUID
    name: str
    series_type: str = Field(default="endterm", pattern=r"^(midterm|endterm|mock|test)$")
    start_date: date
    end_date: date
    weight_percentage: float = Field(default=30.0, ge=0, le=100)


class ExamSeriesOut(BaseModel):
    id: uuid.UUID
    name: str
    series_type: str
    start_date: date
    end_date: date
    is_published: bool
    weight_percentage: float
    model_config = {"from_attributes": True}


class ExamPaperCreate(BaseModel):
    series_id: uuid.UUID
    subject_id: uuid.UUID
    class_id: uuid.UUID
    name: str
    paper_code: str | None = None
    max_score: float = Field(gt=0)
    weight: float = Field(default=1.0, ge=0)
    duration_minutes: int | None = None
    exam_date: date | None = None
    instructions: str | None = None


class ExamPaperOut(BaseModel):
    id: uuid.UUID
    name: str
    paper_code: str | None
    subject_id: uuid.UUID
    class_id: uuid.UUID
    max_score: float
    weight: float
    duration_minutes: int | None
    exam_date: date | None
    model_config = {"from_attributes": True}


class ExamScoreEntry(BaseModel):
    student_id: uuid.UUID
    score: float = Field(ge=0)
    is_absent: bool = False
    remarks: str | None = None
