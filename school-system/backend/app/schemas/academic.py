"""Academic structure schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class AcademicYearCreate(BaseModel):
    name: str
    start_date: date
    end_date: date
    is_current: bool = False


class AcademicYearOut(BaseModel):
    id: uuid.UUID
    name: str
    start_date: date
    end_date: date
    is_current: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class TermCreate(BaseModel):
    academic_year_id: uuid.UUID
    name: str
    term_number: int = Field(ge=1)
    start_date: date
    end_date: date
    is_current: bool = False


class TermOut(BaseModel):
    id: uuid.UUID
    academic_year_id: uuid.UUID
    name: str
    term_number: int
    start_date: date
    end_date: date
    is_current: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class ClassCreate(BaseModel):
    name: str
    level: int | None = Field(default=None, ge=0)
    description: str | None = None


class ClassOut(BaseModel):
    id: uuid.UUID
    name: str
    level: int | None = None
    description: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class StreamCreate(BaseModel):
    class_id: uuid.UUID
    name: str


class StreamOut(BaseModel):
    id: uuid.UUID
    class_id: uuid.UUID
    name: str
    created_at: datetime
    model_config = {"from_attributes": True}


class SubjectCreate(BaseModel):
    code: str
    name: str
    description: str | None = None
    department_id: uuid.UUID | None = None


class SubjectOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None = None
    department_id: uuid.UUID | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class DepartmentCreate(BaseModel):
    name: str
    description: str | None = None


class DepartmentOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}
