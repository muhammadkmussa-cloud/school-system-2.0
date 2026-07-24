"""School Management System — Teacher Provisioning Service.

Handles bulk teacher account generation during school onboarding.
All business logic for creating teacher accounts, generating credentials,
and managing the provisioning workflow lives here.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.teacher import Teacher
from app.models.user import User


@dataclass
class TeacherCredential:
    id: str
    employee_number: str
    full_name: str
    email: str
    temp_password: str
    is_active: bool


@dataclass
class ProvisioningResult:
    created: int
    teachers: list[TeacherCredential]


class TeacherProvisioningService:
    """Service for bulk teacher account creation and management."""

    def __init__(self, db: AsyncSession, school_id: uuid.UUID):
        self.db = db
        self.school_id = school_id

    async def provision_teachers(self, count: int) -> ProvisioningResult:
        """Generate *count* teacher accounts with temp credentials."""
        if count < 1:
            raise ValueError("count must be at least 1")
        if count > settings.MAX_TEACHERS_PER_SCHOOL:
            raise ValueError(
                f"count cannot exceed {settings.MAX_TEACHERS_PER_SCHOOL}"
            )

        existing = await self.db.scalar(
            select(func.count(Teacher.id)).where(
                Teacher.school_id == self.school_id
            )
        ) or 0
        if existing + count > settings.MAX_TEACHERS_PER_SCHOOL:
            raise ValueError(
                f"Total teachers would exceed limit of {settings.MAX_TEACHERS_PER_SCHOOL}"
            )

        from app.models.school import School
        school = await self.db.scalar(
            select(School).where(School.id == self.school_id)
        )
        school_code = school.code.lower() if school else "sch"

        created = []
        for i in range(count):
            num = existing + i + 1
            emp_number = f"TCH{num:04d}"
            username = f"teacher.{emp_number.lower()}"
            temp_email = f"{username}@{school_code}.temp.example.com"
            temp_password = uuid.uuid4().hex[:12]

            user = User(
                school_id=self.school_id,
                username=username,
                email=temp_email,
                hashed_password=hash_password(temp_password),
                full_name=f"Teacher {num:04d}",
                role="teacher",
                status="pending_first_login",
                must_change_password=True,
                is_verified=False,
            )
            self.db.add(user)
            await self.db.flush()

            teacher = Teacher(
                school_id=self.school_id,
                user_id=user.id,
                employee_number=emp_number,
                full_name=f"Teacher {num:04d}",
                email=temp_email,
            )
            teacher.is_active = False
            self.db.add(teacher)
            await self.db.flush()

            created.append(TeacherCredential(
                id=str(teacher.id),
                employee_number=emp_number,
                full_name=f"Teacher {num:04d}",
                email=temp_email,
                temp_password=temp_password,
                is_active=False,
            ))

        return ProvisioningResult(created=count, teachers=created)

    async def provision_from_list(
        self, staff_list: list[dict[str, Any]]
    ) -> ProvisioningResult:
        """Create teacher accounts from a validated staff list.

        Each entry should have: full_name, email, employee_number (optional),
        phone (optional), subjects (optional list), classes (optional list).
        """
        from app.models.school import School
        school = await self.db.scalar(
            select(School).where(School.id == self.school_id)
        )
        school_code = school.code.lower() if school else "sch"

        existing = await self.db.scalar(
            select(func.count(Teacher.id)).where(
                Teacher.school_id == self.school_id
            )
        ) or 0

        created = []
        for i, entry in enumerate(staff_list):
            num = existing + i + 1
            full_name = entry.get("full_name", "").strip()
            email = entry.get("email", "").strip()
            if not email:
                email = f"teacher{num:04d}@{school_code}.temp.example.com"
            emp_number = entry.get("employee_number", "").strip() or f"TCH{num:04d}"
            username = f"teacher.{emp_number.lower()}"
            phone = entry.get("phone", "").strip() or None
            temp_password = uuid.uuid4().hex[:12]

            user = User(
                school_id=self.school_id,
                username=username,
                email=email,
                hashed_password=hash_password(temp_password),
                full_name=full_name or f"Teacher {num:04d}",
                role="teacher",
                status="pending_first_login",
                must_change_password=True,
                is_verified=False,
            )
            self.db.add(user)
            await self.db.flush()

            teacher = Teacher(
                school_id=self.school_id,
                user_id=user.id,
                employee_number=emp_number,
                full_name=full_name or f"Teacher {num:04d}",
                email=email,
                phone=phone,
            )
            teacher.is_active = False
            self.db.add(teacher)
            await self.db.flush()

            created.append(TeacherCredential(
                id=str(teacher.id),
                employee_number=emp_number,
                full_name=full_name or f"Teacher {num:04d}",
                email=email,
                temp_password=temp_password,
                is_active=False,
            ))

        return ProvisioningResult(created=len(created), teachers=created)

    async def reset_password(self, teacher_id: uuid.UUID) -> str:
        """Reset a single teacher's password. Returns the new password."""
        teacher = await self.db.scalar(
            select(Teacher).where(
                Teacher.id == teacher_id,
                Teacher.school_id == self.school_id,
            )
        )
        if not teacher:
            raise ValueError("Teacher not found")

        user = await self.db.scalar(
            select(User).where(User.id == teacher.user_id)
        )
        if not user:
            raise ValueError("User account not found")

        new_password = uuid.uuid4().hex[:12]
        user.hashed_password = hash_password(new_password)
        user.refresh_token_jti = None
        await self.db.flush()
        return new_password

    async def toggle_active(self, teacher_id: uuid.UUID) -> Teacher:
        """Toggle a teacher's active status."""
        teacher = await self.db.scalar(
            select(Teacher).where(
                Teacher.id == teacher_id,
                Teacher.school_id == self.school_id,
            )
        )
        if not teacher:
            raise ValueError("Teacher not found")
        teacher.is_active = not teacher.is_active
        user = await self.db.scalar(
            select(User).where(User.id == teacher.user_id)
        )
        if user:
            user.is_active = teacher.is_active
        await self.db.flush()
        await self.db.refresh(teacher)
        return teacher
