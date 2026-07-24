"""School schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class SchoolCreate(BaseModel):
    name: str
    code: str
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    subscription_tier: str = "free"


class SchoolUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    is_active: bool | None = None
    subscription_tier: str | None = None


class SchoolOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None
    logo_url: str | None = None
    is_active: bool
    subscription_tier: str
    created_at: datetime

    model_config = {"from_attributes": True}
