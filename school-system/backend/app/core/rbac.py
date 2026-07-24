"""School Management System — Extended Role-Based Access Control.

Implements 7 role tiers with permission-level granularity:

    platform_admin   — cross-school superuser
    school_admin     — school-level admin
    deputy_principal — assists school admin
    head_teacher     — academic oversight, reports, promotion
    class_teacher    — attendance + marks for assigned class
    subject_teacher  — marks + lessons for assigned subjects
    teacher          — base teacher (view-only for assigned)

Every endpoint validates a *permission string* (not just role), so two
roles can share permissions without sharing the role name.

Permission strings follow the pattern:  "resource:action"
Examples:  "students:create", "attendance:write", "reports:export"
"""

from __future__ import annotations

import uuid
from functools import wraps
from typing import Annotated, Callable

from fastapi import Depends, HTTPException, status

from app.core.dependencies import CurrentUser

# ── Role definitions ─────────────────────────────────────────────────

ROLES = {
    "platform_admin": {
        "label": "Platform Administrator",
        "level": 100,
        "permissions": ["*:*"],  # wildcard — everything
    },
    "school_admin": {
        "label": "School Administrator",
        "level": 80,
        "permissions": [
            "students:create", "students:read", "students:update", "students:delete",
            "students:import", "students:promote", "students:transfer",
            "teachers:create", "teachers:read", "teachers:update", "teachers:delete",
            "classes:manage", "streams:manage", "subjects:manage",
            "timetable:manage", "academic:manage",
            "reports:view", "reports:export", "reports:generate",
            "settings:manage", "users:manage",
        ],
    },
    "deputy_principal": {
        "label": "Deputy Principal",
        "level": 70,
        "permissions": [
            "students:read", "students:update", "students:promote", "students:transfer",
            "teachers:read",
            "reports:view", "reports:export", "reports:generate",
            "attendance:read", "marks:read",
            "analytics:view",
        ],
    },
    "head_teacher": {
        "label": "Head Teacher / Academic Master",
        "level": 60,
        "permissions": [
            "students:read", "students:promote",
            "teachers:read",
            "classes:manage", "subjects:manage",
            "timetable:manage",
            "reports:view", "reports:export", "reports:generate",
            "attendance:read", "marks:read",
            "exams:manage",
            "analytics:view", "lessons:view_all",
        ],
    },
    "class_teacher": {
        "label": "Class Teacher",
        "level": 40,
        "permissions": [
            "students:read",
            "attendance:write", "attendance:read",
            "marks:write", "marks:read",
            "lessons:write", "lessons:read",
            "reports:view",
            "timetable:view",
        ],
    },
    "subject_teacher": {
        "label": "Subject Teacher",
        "level": 30,
        "permissions": [
            "students:read",
            "marks:write", "marks:read",
            "lessons:write", "lessons:read",
            "reports:view",
            "timetable:view",
        ],
    },
    "teacher": {
        "label": "Teacher",
        "level": 20,
        "permissions": [
            "students:read",
            "attendance:write", "attendance:read",
            "marks:write", "marks:read",
            "lessons:write", "lessons:read",
            "timetable:view",
        ],
    },
}


def get_permissions(role: str) -> set[str]:
    """Return the effective permission set for *role*."""
    entry = ROLES.get(role, ROLES["teacher"])
    return set(entry["permissions"])


def has_permission(role: str, permission: str) -> bool:
    """Check if *role* holds *permission* (wildcard-aware)."""
    perms = get_permissions(role)
    if "*:*" in perms:
        return True
    resource, _, action = permission.partition(":")
    if f"{resource}:*" in perms:
        return True
    return permission in perms


def require_permission(permission: str):
    """FastAPI dependency factory: only pass if current user has *permission*."""

    async def _check(current_user: CurrentUser) -> CurrentUser:
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required",
            )
        return current_user

    return _check


# ── Convenience dependency aliases ───────────────────────────────────

RequireStudentPromote   = Annotated[CurrentUser, Depends(require_permission("students:promote"))]
RequireStudentImport    = Annotated[CurrentUser, Depends(require_permission("students:import"))]
RequireExamsManage      = Annotated[CurrentUser, Depends(require_permission("exams:manage"))]
