"""School Management System — Audit Log Service.

Provides a clean interface for writing audit log entries
from anywhere in the application.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


async def log_account_event(
    db: AsyncSession,
    school_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    actor_role: str | None,
    actor_name: str | None,
    action: str,
    target_user_id: str | None = None,
    target_email: str | None = None,
    changes: dict | None = None,
    ip_address: str | None = None,
    endpoint: str | None = None,
) -> AuditLog:
    """Write an account-related audit entry."""
    summary = _build_summary(action, target_email, changes)
    entry = AuditLog(
        school_id=school_id,
        actor_id=actor_id,
        actor_role=actor_role,
        actor_name=actor_name,
        action=action,
        entity_type="user",
        entity_id=target_user_id,
        changes=changes,
        summary=summary,
        ip_address=ip_address,
        endpoint=endpoint,
    )
    db.add(entry)
    await db.flush()
    return entry


def _build_summary(action: str, email: str | None, changes: dict | None) -> str:
    summaries = {
        "teacher_created": f"Teacher account created for {email or 'unknown'}",
        "temp_password_generated": f"Temporary password generated for {email or 'unknown'}",
        "first_login_completed": f"First login completed by {email or 'unknown'}",
        "password_reset_by_admin": f"Password reset by admin for {email or 'unknown'}",
        "password_changed": f"Password changed by {email or 'unknown'}",
        "account_locked": f"Account locked: {email or 'unknown'}",
        "account_unlocked": f"Account unlocked: {email or 'unknown'}",
        "account_disabled": f"Account disabled: {email or 'unknown'}",
        "account_enabled": f"Account enabled: {email or 'unknown'}",
        "failed_login": f"Failed login attempt for {email or 'unknown'}",
    }
    return summaries.get(action, f"{action}: {email or 'unknown'}")
