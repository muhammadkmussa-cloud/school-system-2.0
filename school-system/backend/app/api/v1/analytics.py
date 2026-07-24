"""Analytics API — school intelligence & trends."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DB, RequireStaff
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/overview")
async def school_overview(db: DB, current_user: RequireStaff):
    """One-page school health snapshot."""
    svc = AnalyticsService(db, current_user.school_id)
    return await svc.school_overview()


@router.get("/attendance-trend")
async def attendance_trend(
    db: DB,
    current_user: RequireStaff,
    days: int = Query(30, le=365),
):
    """Daily attendance percentages for trend charts."""
    svc = AnalyticsService(db, current_user.school_id)
    return await svc.attendance_trend(days)


@router.get("/gender-analysis")
async def gender_analysis(
    db: DB,
    current_user: RequireStaff,
    term_id: uuid.UUID = Query(...),
):
    """Male vs female performance by subject."""
    svc = AnalyticsService(db, current_user.school_id)
    return await svc.gender_analysis(term_id)


@router.get("/syllabus-coverage")
async def syllabus_coverage(
    db: DB,
    current_user: RequireStaff,
    teacher_id: str = "",
    subject_id: str = "",
):
    """Track how much of the curriculum has been covered."""
    svc = AnalyticsService(db, current_user.school_id)
    return await svc.syllabus_coverage(
        teacher_id=uuid.UUID(teacher_id) if teacher_id else None,
        subject_id=uuid.UUID(subject_id) if subject_id else None,
    )


@router.get("/teacher-effectiveness")
async def teacher_effectiveness(
    db: DB,
    current_user: RequireStaff,
    term_id: uuid.UUID = Query(...),
):
    """Rank teachers by student performance."""
    svc = AnalyticsService(db, current_user.school_id)
    return await svc.teacher_effectiveness(term_id)
