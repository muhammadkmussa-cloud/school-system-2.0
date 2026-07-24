"""Teacher schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class TeacherCreate(BaseModel):
    employee_number: str
    full_name: str
    email: EmailStr
    phone: str | None = None
    password: str | None = None  # auto-generated if omitted


class TeacherUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    is_active: bool | None = None


class TeacherAssignSubjects(BaseModel):
    subject_ids: list[uuid.UUID]


class TeacherAssignClasses(BaseModel):
    class_ids: list[uuid.UUID]


class TeacherOut(BaseModel):
    id: uuid.UUID
    employee_number: str
    full_name: str
    email: str
    phone: str | None = None
    is_active: bool
    user_id: uuid.UUID | None = None
    created_at: datetime

    # User account lifecycle info
    user_status: str | None = None
    must_change_password: bool | None = None

    model_config = {"from_attributes": True}


class TeacherList(BaseModel):
    items: list[TeacherOut]
    total: int
    page: int
    page_size: int


class BulkTeacherCreate(BaseModel):
    count: int = 0


class TeacherCredentials(BaseModel):
    id: uuid.UUID
    employee_number: str
    full_name: str
    email: str
    temp_password: str
    is_active: bool


class BulkTeacherCreateResult(BaseModel):
    created: int
    teachers: list[TeacherCredentials]


class TeacherResetPasswordResult(BaseModel):
    new_password: str
    teacher_id: uuid.UUID
