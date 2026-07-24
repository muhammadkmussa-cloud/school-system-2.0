"""Onboarding schemas — school setup wizard steps."""

from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel, EmailStr, Field


# ── Step 1: School Information ──────────────────────────────────────

class SchoolInfoStep(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=1, max_length=20)
    school_type: str = Field(default="secondary", description="primary | secondary | both")
    curriculum: str = Field(default="kicd", description="kicd | igcse | ib | other")
    country: str = Field(default="Kenya")
    county: str = Field(default="", description="County or region")
    address: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    timezone: str = Field(default="Africa/Nairobi")
    academic_year_name: str = Field(default="2026 Academic Year")
    academic_year_start: date
    academic_year_end: date


# ── Step 2: Academic Structure ──────────────────────────────────────

class GradeConfig(BaseModel):
    name: str
    level: int = Field(ge=0)
    num_streams: int = Field(default=2, ge=1, le=10)


class SubjectConfig(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=200)
    is_elective: bool = False


class AcademicStructureStep(BaseModel):
    grades: list[GradeConfig] = Field(..., min_length=1)
    subjects: list[SubjectConfig] = Field(..., min_length=1)
    term_names: list[str] = Field(default=["Term 1", "Term 2", "Term 3"])
    grading_system: str = Field(default="a-f", description="a-f | percentage | both")


# ── Step 3: Staff Setup — Manual Entry ──────────────────────────────

class StaffEntry(BaseModel):
    full_name: str = Field(..., min_length=1)
    email: EmailStr
    phone: str | None = None
    employee_number: str | None = None
    subjects: list[str] = Field(default_factory=list)
    assigned_classes: list[str] = Field(default_factory=list)
    assigned_streams: list[str] = Field(default_factory=list)


class StaffSetupManual(BaseModel):
    staff_list: list[StaffEntry] = Field(..., min_length=1)


# ── Step 3: Staff Setup — Bulk Import ───────────────────────────────

class StaffSetupBulk(BaseModel):
    file_content: str  # base64-encoded CSV or Excel
    filename: str = Field(..., description="Must end with .csv or .xlsx")


# ── Responses ───────────────────────────────────────────────────────

class TeacherCredentialOut(BaseModel):
    id: str
    employee_number: str
    full_name: str
    email: str
    temp_password: str
    is_active: bool


class OnboardingStepResponse(BaseModel):
    step: int
    status: str = "completed"
    message: str = ""


class StaffProvisioningResult(BaseModel):
    total_created: int
    teachers: list[TeacherCredentialOut]


class ValidationError(BaseModel):
    row: int
    field: str
    message: str


class StaffValidationResult(BaseModel):
    valid: bool
    total_rows: int
    valid_rows: int
    errors: list[ValidationError]
    preview: list[dict] = Field(default_factory=list)
