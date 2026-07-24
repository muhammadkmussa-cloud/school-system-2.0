"""School Management System — RBAC Enforcement Decorator.

Wraps FastAPI route handlers with automatic:
- Permission checking (via rbac.has_permission)
- School-scoping validation (school_id in JWT matches resource)
- Audit logging (optional)
- Rate limiting placeholder

Usage:
    @enforce("students:create")
    async def create_student(...): ...

    @enforce("attendance:write", audit=True)
    async def record_attendance(...): ...

    @enforce("reports:export", rate_limit="10/minute")
    async def export_report(...): ...
"""

from __future__ import annotations

import functools
import inspect
from typing import Any, Callable

from fastapi import HTTPException, Request, status

from app.core.rbac import has_permission


def enforce(
    permission: str,
    *,
    audit: bool = False,
    rate_limit: str | None = None,
    school_scoped: bool = True,
):
    """Decorate a FastAPI route handler with RBAC + optional features.

    Assumes the handler receives `current_user` as a parameter.
    """

    def decorator(func: Callable) -> Callable:
        sig = inspect.signature(func)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract current_user from kwargs
            current_user = kwargs.get("current_user")
            if current_user is None:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="RBAC: no current_user in handler signature",
                )

            # Check permission
            if not has_permission(current_user.role, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required. Your role: '{current_user.role}'",
                )

            # School scoping: ensure school_id in path/body matches user's school
            if school_scoped and current_user.role != "platform_admin":
                await _validate_school_scope(kwargs, current_user)

            # Rate limiting placeholder
            if rate_limit:
                pass  # Production: check Redis rate limiter

            # Execute handler
            result = await func(*args, **kwargs)

            # Audit placeholder
            if audit:
                pass  # Production: log to AuditService

            return result

        return wrapper

    return decorator


async def _validate_school_scope(kwargs: dict, current_user: Any):
    """Ensure the requested resource belongs to the user's school."""
    db = kwargs.get("db")
    if db is None:
        return

    from sqlalchemy import select

    # Check student_id
    student_id = kwargs.get("student_id")
    if student_id:
        from app.models.student import Student
        student = await db.scalar(
            select(Student).where(Student.id == student_id)
        )
        if student and str(student.school_id) != str(current_user.school_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found",
            )

    # Check class_id
    class_id = kwargs.get("class_id")
    if class_id:
        from app.models.academic import Class_
        klass = await db.scalar(
            select(Class_).where(Class_.id == class_id)
        )
        if klass and str(klass.school_id) != str(current_user.school_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resource not found",
            )


# ── RBAC route map ──────────────────────────────────────────────────
# Maps every API route to its required permission for documentation.
# This serves as the single source of truth for the permission matrix.

RBAC_ROUTE_MAP: dict[str, dict[str, str]] = {
    # Auth
    "POST /api/v1/auth/login":                {"perm": "auth:login",           "public": True},
    "POST /api/v1/auth/refresh":              {"perm": "auth:refresh",         "public": True},
    "POST /api/v1/auth/change-password":      {"perm": "auth:change_password", "public": False},
    "POST /api/v1/auth/logout":               {"perm": "auth:logout",          "public": False},
    "GET  /api/v1/auth/me":                   {"perm": "auth:me",              "public": False},

    # Users
    "GET  /api/v1/users":                     {"perm": "users:read",           "public": False},
    "POST /api/v1/users":                     {"perm": "users:create",         "public": False},
    "GET  /api/v1/users/{user_id}":           {"perm": "users:read",           "public": False},
    "PATCH /api/v1/users/{user_id}":          {"perm": "users:update",         "public": False},
    "POST /api/v1/users/{user_id}/reset-password": {"perm": "users:manage",    "public": False},

    # Schools
    "GET  /api/v1/schools":                   {"perm": "schools:read",         "public": False},
    "POST /api/v1/schools":                   {"perm": "schools:create",       "public": False},
    "GET  /api/v1/schools/{school_id}":       {"perm": "schools:read",         "public": False},
    "PATCH /api/v1/schools/{school_id}":      {"perm": "schools:update",       "public": False},
    "POST /api/v1/schools/{school_id}/toggle-active": {"perm": "schools:manage", "public": False},

    # Students
    "GET  /api/v1/students":                  {"perm": "students:read",        "public": False},
    "POST /api/v1/students":                  {"perm": "students:create",      "public": False},
    "GET  /api/v1/students/{student_id}":     {"perm": "students:read",        "public": False},
    "PATCH /api/v1/students/{student_id}":    {"perm": "students:update",      "public": False},
    "POST /api/v1/students/{student_id}/transfer": {"perm": "students:transfer", "public": False},
    "POST /api/v1/students/{student_id}/promote":  {"perm": "students:promote",  "public": False},
    "POST /api/v1/students/{student_id}/archive":  {"perm": "students:delete",   "public": False},

    # Teachers
    "GET  /api/v1/teachers":                  {"perm": "teachers:read",        "public": False},
    "POST /api/v1/teachers":                  {"perm": "teachers:create",      "public": False},
    "POST /api/v1/teachers/bulk":             {"perm": "teachers:create",      "public": False},
    "GET  /api/v1/teachers/credentials":      {"perm": "teachers:read",        "public": False},
    "GET  /api/v1/teachers/{teacher_id}":     {"perm": "teachers:read",        "public": False},
    "PATCH /api/v1/teachers/{teacher_id}":    {"perm": "teachers:update",      "public": False},
    "POST /api/v1/teachers/{teacher_id}/toggle-active": {"perm": "teachers:manage", "public": False},
    "POST /api/v1/teachers/{teacher_id}/reset-password": {"perm": "teachers:manage", "public": False},
    "POST /api/v1/teachers/{teacher_id}/lock":           {"perm": "teachers:manage", "public": False},
    "POST /api/v1/teachers/{teacher_id}/unlock":         {"perm": "teachers:manage", "public": False},
    "POST /api/v1/teachers/{teacher_id}/force-reset":    {"perm": "teachers:manage", "public": False},
    "GET  /api/v1/teachers/{teacher_id}/account-status": {"perm": "teachers:read",   "public": False},

    # Academic
    "GET  /api/v1/academic/years":            {"perm": "academic:read",        "public": False},
    "POST /api/v1/academic/years":            {"perm": "academic:manage",      "public": False},
    "GET  /api/v1/academic/terms":            {"perm": "academic:read",        "public": False},
    "POST /api/v1/academic/terms":            {"perm": "academic:manage",      "public": False},
    "GET  /api/v1/academic/classes":          {"perm": "academic:read",        "public": False},
    "POST /api/v1/academic/classes":          {"perm": "classes:manage",       "public": False},
    "GET  /api/v1/academic/streams":          {"perm": "academic:read",        "public": False},
    "POST /api/v1/academic/streams":          {"perm": "streams:manage",       "public": False},
    "GET  /api/v1/academic/subjects":         {"perm": "academic:read",        "public": False},
    "POST /api/v1/academic/subjects":         {"perm": "subjects:manage",      "public": False},
    "GET  /api/v1/academic/departments":      {"perm": "academic:read",        "public": False},
    "POST /api/v1/academic/departments":      {"perm": "subjects:manage",      "public": False},

    # Timetable
    "GET  /api/v1/timetable":                 {"perm": "timetable:view",       "public": False},
    "POST /api/v1/timetable":                 {"perm": "timetable:manage",     "public": False},
    "GET  /api/v1/timetable/{id}":            {"perm": "timetable:view",       "public": False},
    "POST /api/v1/timetable/{id}/entries":    {"perm": "timetable:manage",     "public": False},
    "DELETE /api/v1/timetable/{id}/entries/{eid}": {"perm": "timetable:manage","public": False},

    # Attendance
    "POST /api/v1/attendance/batch":          {"perm": "attendance:write",     "public": False},
    "GET  /api/v1/attendance/class/{class_id}":{"perm": "attendance:read",     "public": False},
    "GET  /api/v1/attendance/student/{id}":   {"perm": "attendance:read",      "public": False},
    "GET  /api/v1/attendance/stats":          {"perm": "attendance:read",      "public": False},

    # Gradebook
    "GET  /api/v1/gradebook/assessments":     {"perm": "marks:read",           "public": False},
    "POST /api/v1/gradebook/assessments":     {"perm": "marks:write",          "public": False},
    "GET  /api/v1/gradebook/assessments/{id}":{"perm": "marks:read",           "public": False},
    "POST /api/v1/gradebook/assessments/{id}/marks": {"perm": "marks:write",   "public": False},
    "GET  /api/v1/gradebook/assessments/{id}/marks": {"perm": "marks:read",    "public": False},
    "GET  /api/v1/gradebook/assessments/{id}/stats": {"perm": "marks:read",    "public": False},
    "GET  /api/v1/gradebook/student/{id}/grades":    {"perm": "marks:read",    "public": False},

    # Lessons
    "GET  /api/v1/lessons":                   {"perm": "lessons:read",         "public": False},
    "POST /api/v1/lessons":                   {"perm": "lessons:write",        "public": False},
    "POST /api/v1/lessons/duplicate":         {"perm": "lessons:write",        "public": False},
    "GET  /api/v1/lessons/{id}":              {"perm": "lessons:read",         "public": False},
    "PATCH /api/v1/lessons/{id}":             {"perm": "lessons:write",        "public": False},
    "POST /api/v1/lessons/{id}/complete":     {"perm": "lessons:write",        "public": False},

    # Reports
    "GET  /api/v1/reports/attendance":        {"perm": "reports:view",         "public": False},
    "GET  /api/v1/reports/students":          {"perm": "reports:view",         "public": False},
    "GET  /api/v1/reports/teacher-workload":  {"perm": "reports:view",         "public": False},
    "GET  /api/v1/reports/subject-performance":{"perm": "reports:view",        "public": False},

    # Results
    "GET  /api/v1/results/student/{id}/report-card":    {"perm": "reports:view", "public": False},
    "GET  /api/v1/results/student/{id}/report-card/pdf":{"perm": "reports:export","public": False},
    "GET  /api/v1/results/class/{id}/summary":          {"perm": "reports:view",  "public": False},
    "GET  /api/v1/results/class/{id}/rankings":         {"perm": "reports:view",  "public": False},

    # Exams
    "GET  /api/v1/exams/series":              {"perm": "exams:read",           "public": False},
    "POST /api/v1/exams/series":              {"perm": "exams:manage",         "public": False},
    "POST /api/v1/exams/papers":              {"perm": "exams:manage",         "public": False},
    "GET  /api/v1/exams/papers/{id}":         {"perm": "exams:read",           "public": False},
    "POST /api/v1/exams/papers/{id}/scores":  {"perm": "exams:manage",         "public": False},
    "GET  /api/v1/exams/results/student/{id}":{"perm": "exams:read",           "public": False},
    "GET  /api/v1/exams/results/class/{id}/ranking": {"perm": "exams:read",    "public": False},

    # Analytics
    "GET  /api/v1/analytics/overview":         {"perm": "analytics:view",      "public": False},
    "GET  /api/v1/analytics/attendance-trend": {"perm": "analytics:view",      "public": False},
    "GET  /api/v1/analytics/gender-analysis":  {"perm": "analytics:view",      "public": False},
    "GET  /api/v1/analytics/syllabus-coverage":{"perm": "analytics:view",      "public": False},
    "GET  /api/v1/analytics/teacher-effectiveness": {"perm": "analytics:view", "public": False},

    # Dashboard
    "GET  /api/v1/dashboard/admin":           {"perm": "dashboard:view",       "public": False},
    "GET  /api/v1/dashboard/teacher":         {"perm": "dashboard:view",       "public": False},

    # Curriculum
    "GET  /api/v1/curriculum":                {"perm": "settings:read",        "public": False},
    "GET  /api/v1/curriculum/{id}":           {"perm": "settings:read",        "public": False},
    "POST /api/v1/curriculum/assign":         {"perm": "settings:manage",      "public": False},
    "GET  /api/v1/curriculum/my/levels":      {"perm": "settings:read",        "public": False},
    "GET  /api/v1/curriculum/my/grade":       {"perm": "marks:read",           "public": False},

    # Workflow
    "GET  /api/v1/workflow/definitions":      {"perm": "settings:read",        "public": False},
    "GET  /api/v1/workflow/definitions/{id}": {"perm": "settings:read",        "public": False},
    "POST /api/v1/workflow/instances/{id}/transition": {"perm": "workflow:approve", "public": False},
    "GET  /api/v1/workflow/instances/{id}/actions":    {"perm": "workflow:view",     "public": False},
    "GET  /api/v1/workflow/instances/{id}/history":    {"perm": "workflow:view",     "public": False},

    # Audit
    "GET  /api/v1/audit":                     {"perm": "audit:view",           "public": False},
    "GET  /api/v1/audit/entity/{type}/{id}":  {"perm": "audit:view",           "public": False},

    # Imports
    "POST /api/v1/imports/students/csv":      {"perm": "students:import",      "public": False},
    "POST /api/v1/imports/teachers/csv":      {"perm": "teachers:create",      "public": False},
    "POST /api/v1/imports/marks/csv":         {"perm": "marks:write",          "public": False},
    "GET  /api/v1/imports/templates/students":{"perm": "students:read",        "public": False},
    "GET  /api/v1/imports/templates/teachers":{"perm": "teachers:read",        "public": False},

    # Promotion
    "POST /api/v1/promotion/class/{id}":      {"perm": "students:promote",     "public": False},
    "POST /api/v1/promotion/rollback":        {"perm": "students:promote",     "public": False},
    "GET  /api/v1/promotion/path/{id}":       {"perm": "students:read",        "public": False},

    # Notifications
    "GET  /api/v1/notifications":             {"perm": "notifications:read",   "public": False},
    "POST /api/v1/notifications/{id}/read":   {"perm": "notifications:read",   "public": False},
    "POST /api/v1/notifications/read-all":    {"perm": "notifications:read",   "public": False},
    "GET  /api/v1/notifications/unread-count":{"perm": "notifications:read",   "public": False},
    "POST /api/v1/notifications/send":        {"perm": "notifications:send",   "public": False},

    # Sync
    "POST /api/v1/sync/push":                 {"perm": "sync:push",            "public": False},
    "GET  /api/v1/sync/status":               {"perm": "sync:read",            "public": False},

    # Onboarding / Setup
    "POST /api/v1/onboarding/setup/step-1":              {"perm": "settings:manage",  "public": False},
    "POST /api/v1/onboarding/setup/step-2":              {"perm": "settings:manage",  "public": False},
    "POST /api/v1/onboarding/setup/step-3/manual":       {"perm": "teachers:create",  "public": False},
    "POST /api/v1/onboarding/setup/step-3/validate":     {"perm": "teachers:create",  "public": False},
    "POST /api/v1/onboarding/setup/step-3/confirm":      {"perm": "teachers:create",  "public": False},
    "GET  /api/v1/onboarding/setup/staff-template":      {"perm": "teachers:read",    "public": False},
    "GET  /api/v1/onboarding/setup/status":              {"perm": "settings:manage",  "public": False},

    # Platform Admin
    "GET  /api/v1/platform/dashboard":        {"perm": "dashboard:view",       "public": False},
    "GET  /api/v1/platform/schools/stats":    {"perm": "schools:read",         "public": False},
    "GET  /api/v1/platform/users/summary":    {"perm": "users:read",           "public": False},
}

# ── Permission matrix for all 7 roles (generated from RBAC_ROUTE_MAP) ──

def generate_permission_matrix() -> dict[str, dict[str, bool]]:
    """Generate a matrix of role → route → allowed."""
    from app.core.rbac import ROLES

    matrix: dict[str, dict[str, bool]] = {}
    for role_name in ROLES:
        matrix[role_name] = {}
        for route, meta in RBAC_ROUTE_MAP.items():
            if meta.get("public"):
                matrix[role_name][route] = True
            else:
                matrix[role_name][route] = has_permission(role_name, meta["perm"])
    return matrix
