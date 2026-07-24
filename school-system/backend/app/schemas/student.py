"""Student schemas."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class StudentCreate(BaseModel):
    admission_number: str = Field(min_length=1, max_length=50)
    full_name: str
    gender: str = Field(..., pattern=r"^(male|female|other)$")
    date_of_birth: date
    class_id: uuid.UUID
    stream_id: uuid.UUID | None = None
    academic_year_id: uuid.UUID
    parent_name: str | None = None
    parent_phone: str | None = None
    parent_email: str | None = None
    medical_notes: str | None = None


class StudentUpdate(BaseModel):
    full_name: str | None = None
    gender: str | None = None
    date_of_birth: date | None = None
    class_id: uuid.UUID | None = None
    stream_id: uuid.UUID | None = None
    parent_name: str | None = None
    parent_phone: str | None = None
    parent_email: str | None = None
    medical_notes: str | None = None
    status: str | None = None


class StudentTransfer(BaseModel):
    new_class_id: uuid.UUID
    new_stream_id: uuid.UUID | None = None


class StudentPromote(BaseModel):
    target_class_id: uuid.UUID
    target_academic_year_id: uuid.UUID


class StudentOut(BaseModel):
    id: uuid.UUID
    admission_number: str
    full_name: str
    gender: str
    date_of_birth: date
    class_id: uuid.UUID
    stream_id: uuid.UUID | None = None
    academic_year_id: uuid.UUID
    parent_name: str | None = None
    parent_phone: str | None = None
    parent_email: str | None = None
    medical_notes: str | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class StudentList(BaseModel):
    items: list[StudentOut]
    total: int
    page: int
    page_size: int
