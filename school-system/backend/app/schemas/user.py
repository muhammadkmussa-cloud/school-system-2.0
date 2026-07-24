"""User schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    phone: str | None = None
    last_login_at: datetime | None = None
    school_id: uuid.UUID
    created_at: datetime

    # Account lifecycle (replaces is_active + is_verified)
    username: str | None = None
    status: str = "active"
    must_change_password: bool = False
    terms_accepted: bool = False
    profile_completed: bool = False
    password_changed_at: datetime | None = None
    is_active: bool = True
    is_verified: bool = True

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    role: str  # "school_admin" | "teacher"
    phone: str | None = None
    password: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    status: str | None = None


class UserList(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int
