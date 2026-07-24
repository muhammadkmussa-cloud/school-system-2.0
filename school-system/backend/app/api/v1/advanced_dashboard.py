"""Advanced Dashboard API — executive summary, heatmaps, at-risk, comparisons."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DB, RequireStaff, RequireSchoolAdmin
from app.services.dashboard.advanced_dashboard import AdvancedDashboardService

router = APIRouter()


@router.get("/executive-summary")
async def executive_summary(db: DB, current_user: RequireStaff):
    """One-page KPI snapshot for administrators."""
    svc = AdvancedDashboardService(db, current_user.school_id)
    return await svc.executive_summary()


@router.get("/performance-heatmap")
async def performance_heatmap(
    term_id: uuid.UUID = Query(...),
    db: DB = None,
    current_user: RequireSchoolAdmin = None,
):
    """Subject × Class performance matrix as a heatmap."""
    svc = AdvancedDashboardService(db, current_user.school_id)
    return await svc.performance_heatmap(term_id)


@router.get("/at-risk-students")
async def at_risk_students(
    term_id: uuid.UUID = Query(...),
    threshold: float = Query(40.0, description="Mean percentage below which student is at risk"),
    db: DB = None,
    current_user: RequireSchoolAdmin = None,
):
    """Students below academic threshold or with poor attendance."""
    svc = AdvancedDashboardService(db, current_user.school_id)
    return {"students": await svc.at_risk_students(term_id, threshold)}


@router.get("/term-comparison")
async def term_comparison(
    term1_id: uuid.UUID = Query(...),
    term2_id: uuid.UUID = Query(...),
    db: DB = None,
    current_user: RequireSchoolAdmin = None,
):
    """Compare performance between two terms."""
    svc = AdvancedDashboardService(db, current_user.school_id)
    return await svc.term_comparison(term1_id, term2_id)


@router.get("/stream-comparison")
async def stream_comparison(
    class_id: uuid.UUID = Query(...),
    term_id: uuid.UUID = Query(...),
    db: DB = None,
    current_user: RequireSchoolAdmin = None,
):
    """Compare performance across streams within a class."""
    svc = AdvancedDashboardService(db, current_user.school_id)
    return {"streams": await svc.stream_comparison(class_id, term_id)}


@router.get("/teacher-leaderboard")
async def teacher_leaderboard(
    term_id: uuid.UUID = Query(...),
    db: DB = None,
    current_user: RequireSchoolAdmin = None,
):
    """Rank teachers by composite performance score."""
    svc = AdvancedDashboardService(db, current_user.school_id)
    return {"leaderboard": await svc.teacher_leaderboard(term_id)}
