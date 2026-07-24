"""Student promotion API — bulk promote, rollback, and promotion paths."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status

from app.core.dependencies import DB
from app.core.rbac import RequireStudentPromote
from app.services.promotion_service import PromotionService

router = APIRouter()


@router.post("/class/{class_id}")
async def promote_class(
    class_id: uuid.UUID,
    db: DB,
    current_user: RequireStudentPromote,
    target_class_id: uuid.UUID = Query(...),
    target_academic_year_id: uuid.UUID = Query(...),
    min_mean: float | None = Query(None),
):
    """Promote all eligible students from a class to the next class."""
    svc = PromotionService(db, current_user.school_id)

    # Parse override/retain lists from body if provided
    result = await svc.promote_class(
        source_class_id=class_id,
        target_class_id=target_class_id,
        target_academic_year_id=target_academic_year_id,
        min_mean=min_mean,
    )
    return {
        "promoted": result.promoted,
        "retained": result.retained,
        "graduated": result.graduated,
        "errors": result.errors,
    }


@router.post("/rollback")
async def rollback_promotion(
    db: DB,
    current_user: RequireStudentPromote,
):
    """Undo the last promotion (restore from snapshot)."""
    svc = PromotionService(db, current_user.school_id)
    result = await svc.rollback()
    if result.errors:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.errors)
    return {"restored": result.promoted}


@router.get("/path/{class_id}")
async def promotion_path(
    class_id: uuid.UUID,
    db: DB,
    current_user: RequireStudentPromote,
):
    """Get the promotion chain for a class (Form 1 → Form 2 → ... → graduated)."""
    svc = PromotionService(db, current_user.school_id)
    chain = await svc.get_promotion_path(class_id)
    return {"chain": chain}
