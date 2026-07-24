"""School Management System — Credential Service.

Handles temporary password generation, batch credential exports,
and secure display of credentials during onboarding.
"""

from __future__ import annotations

import csv
import io
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.teacher import Teacher
from app.models.user import User


@dataclass
class CredentialEntry:
    employee_number: str
    full_name: str
    email: str
    temp_password: str
    is_active: bool


class CredentialService:
    """Manages credential generation and export."""

    def __init__(self, db: AsyncSession, school_id: uuid.UUID):
        self.db = db
        self.school_id = school_id

    async def generate_batch_passwords(
        self, teacher_ids: list[uuid.UUID]
    ) -> list[CredentialEntry]:
        """Generate new temp passwords for a batch of teachers."""
        entries = []
        for tid in teacher_ids:
            teacher = await self.db.scalar(
                select(Teacher).where(
                    Teacher.id == tid,
                    Teacher.school_id == self.school_id,
                )
            )
            if not teacher:
                continue

            user = await self.db.scalar(
                select(User).where(User.id == teacher.user_id)
            )
            if not user:
                continue

            new_password = uuid.uuid4().hex[:12]
            user.hashed_password = hash_password(new_password)
            user.refresh_token_jti = None

            entries.append(CredentialEntry(
                employee_number=teacher.employee_number,
                full_name=teacher.full_name,
                email=teacher.email,
                temp_password=new_password,
                is_active=teacher.is_active,
            ))

        await self.db.flush()
        return entries

    async def export_csv(self) -> str:
        """Export all teacher credentials as CSV."""
        teachers = await self.db.scalars(
            select(Teacher).where(Teacher.school_id == self.school_id)
            .order_by(Teacher.employee_number)
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Employee #", "Full Name", "Email (Username)", "Status"])

        for teacher in teachers.all():
            writer.writerow([
                teacher.employee_number,
                teacher.full_name,
                teacher.email,
                "Active" if teacher.is_active else "Pending Activation",
            ])

        return output.getvalue()

    async def get_current_credentials(
        self, include_passwords: bool = False
    ) -> list[CredentialEntry]:
        """Get credentials for all teachers in the school."""
        teachers = await self.db.scalars(
            select(Teacher).where(Teacher.school_id == self.school_id)
            .order_by(Teacher.employee_number)
        )

        entries = []
        for teacher in teachers.all():
            password = ""
            if include_passwords:
                new_pw = uuid.uuid4().hex[:12]
                user = await self.db.scalar(
                    select(User).where(User.id == teacher.user_id)
                )
                if user:
                    user.hashed_password = hash_password(new_pw)
                    password = new_pw

            entries.append(CredentialEntry(
                employee_number=teacher.employee_number,
                full_name=teacher.full_name,
                email=teacher.email,
                temp_password=password,
                is_active=teacher.is_active,
            ))

        if include_passwords:
            await self.db.flush()

        return entries
