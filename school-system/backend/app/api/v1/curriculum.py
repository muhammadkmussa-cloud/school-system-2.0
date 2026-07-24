"""Curriculum API — list, assign, grade."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DB, RequireSchoolAdmin
from app.services.curriculum.curriculum_service import CurriculumService

router = APIRouter()


@router.get("")
async def list_curricula(db: DB, current_user: CurrentUser):
    """List all available curricula."""
    svc = CurriculumService(db)
    curricula = await svc.list_curricula()
    return [
        {
            "id": str(c.id), "name": c.name, "code": c.code,
            "country": c.country, "description": c.description,
            "is_active": c.is_active,
        }
        for c in curricula
    ]


@router.get("/{curriculum_id}")
async def get_curriculum(curriculum_id: uuid.UUID, db: DB, current_user: CurrentUser):
    svc = CurriculumService(db)
    curr = await svc.get_curriculum(curriculum_id)
    if not curr:
        return {"detail": "Not found"}
    levels = await svc.get_levels(curriculum_id)
    scheme = await svc.get_grading_scheme(curriculum_id)
    bands = await svc.get_grade_bands(scheme.id) if scheme else []

    return {
        "id": str(curr.id), "name": curr.name, "code": curr.code,
        "country": curr.country, "description": curr.description,
        "levels": [{"name": l.name, "code": l.code, "order": l.sort_order, "terminal": l.is_terminal} for l in levels],
        "grading": {
            "name": scheme.name if scheme else "",
            "bands": [{"letter": b.letter, "min": b.min_percentage, "max": b.max_percentage,
                       "points": b.points, "remark": b.remark} for b in bands],
        } if scheme else None,
    }


@router.post("/assign")
async def assign_curriculum(
    curriculum_id: uuid.UUID = Query(...),
    db: DB = None,
    current_user: RequireSchoolAdmin = None,
):
    """Assign a curriculum to the current school."""
    svc = CurriculumService(db)
    sc = await svc.assign_school_curriculum(current_user.school_id, curriculum_id)
    return {"school_id": str(sc.school_id), "curriculum_id": str(sc.curriculum_id)}


@router.get("/my/levels")
async def my_levels(db: DB, current_user: CurrentUser):
    """Get levels for the school's assigned curriculum."""
    svc = CurriculumService(db)
    curriculum = await svc.get_school_curriculum(current_user.school_id)
    if not curriculum:
        return {"levels": []}
    levels = await svc.get_levels(curriculum.id)
    return {"curriculum": curriculum.name, "levels": [
        {"name": l.name, "code": l.code, "order": l.sort_order, "terminal": l.is_terminal}
        for l in levels
    ]}


@router.get("/my/grade")
async def compute_grade(
    percentage: float = Query(...),
    db: DB = None,
    current_user: CurrentUser = None,
):
    """Compute grade letter + points for a percentage under the school's curriculum."""
    svc = CurriculumService(db)
    curriculum = await svc.get_school_curriculum(current_user.school_id)
    if not curriculum:
        return {"letter": "N/A", "points": 0, "remark": "No curriculum assigned"}

    letter, points, remark = await svc.grade_for(curriculum.id, percentage)
    return {"percentage": percentage, "letter": letter, "points": points, "remark": remark}
