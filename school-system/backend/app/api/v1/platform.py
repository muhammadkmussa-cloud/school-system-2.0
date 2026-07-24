"""Platform admin routes — cross-school management & SaaS metrics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.dependencies import DB, RequirePlatformAdmin
from app.models.school import School
from app.models.user import User
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.audit import AuditLog

router = APIRouter()


@router.get("/dashboard")
async def platform_dashboard(db: DB, current_user: RequirePlatformAdmin):
    """Aggregated SaaS metrics for the platform admin."""

    total_schools = await db.scalar(
        select(func.count(School.id))
    )
    active_schools = await db.scalar(
        select(func.count(School.id)).where(School.is_active == True)
    )
    total_users = await db.scalar(
        select(func.count(User.id)).where(User.status == "active")
    )
    total_students = await db.scalar(
        select(func.count(Student.id))
    )
    total_teachers = await db.scalar(
        select(func.count(Teacher.id))
    )

    # Schools registered in last 30 days
    new_schools_30d = await db.scalar(
        select(func.count(School.id)).where(
            School.created_at >= datetime.now(timezone.utc) - timedelta(days=30)
        )
    )

    # Find the school with the most students
    top_school = await db.execute(
        select(School.name, func.count(Student.id).label("student_count"))
        .join(Student, Student.school_id == School.id, isouter=True)
        .group_by(School.id, School.name)
        .order_by(func.count(Student.id).desc())
        .limit(1)
    )
    top_school_row = top_school.first()

    # Recent audit events (platform-wide)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_audits = await db.scalar(
        select(func.count(AuditLog.id)).where(
            AuditLog.created_at >= thirty_days_ago
        )
    )

    # Admin users count
    platform_admins = await db.scalar(
        select(func.count(User.id)).where(User.role == "platform_admin")
    )

    return {
        "total_schools": total_schools or 0,
        "active_schools": active_schools or 0,
        "total_users": total_users or 0,
        "total_students": total_students or 0,
        "total_teachers": total_teachers or 0,
        "platform_admins": platform_admins or 0,
        "new_schools_30d": new_schools_30d or 0,
        "recent_audit_events_30d": recent_audits or 0,
        "top_school_by_students": {
            "name": top_school_row[0] if top_school_row else None,
            "student_count": top_school_row[1] if top_school_row else 0,
        },
    }


@router.get("/schools/stats")
async def platform_schools_stats(db: DB, current_user: RequirePlatformAdmin):
    """Per-school stats for the platform admin."""
    schools = await db.execute(
        select(
            School.id,
            School.name,
            School.code,
            School.is_active,
            School.subscription_tier,
            func.count(Student.id).label("student_count"),
            func.count(Teacher.id).label("teacher_count"),
        )
        .join(Student, Student.school_id == School.id, isouter=True)
        .join(Teacher, Teacher.school_id == School.id, isouter=True)
        .group_by(School.id, School.name, School.code, School.is_active, School.subscription_tier)
        .order_by(School.name)
    )
    return [
        {
            "id": str(row.id),
            "name": row.name,
            "code": row.code,
            "is_active": row.is_active,
            "subscription_tier": row.subscription_tier,
            "student_count": row.student_count or 0,
            "teacher_count": row.teacher_count or 0,
        }
        for row in schools
    ]


@router.get("/users/summary")
async def platform_users_summary(db: DB, current_user: RequirePlatformAdmin):
    """User distribution across roles."""
    rows = await db.execute(
        select(User.role, func.count(User.id).label("count"))
        .group_by(User.role)
        .order_by(User.role)
    )
    return {row.role: row.count for row in rows}
