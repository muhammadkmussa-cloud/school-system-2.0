"""Digital Assignments API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.dependencies import CurrentUser, DB, RequireStaff, Pagination
from app.services.assignments.assignment_service import AssignmentService

router = APIRouter()


@router.get("")
async def list_assignments(
    db: DB,
    current_user: RequireStaff,
    pagination: Pagination = Depends(),
    class_id: str = "",
):
    svc = AssignmentService(db, current_user.school_id, current_user.id)
    assignments, total = await svc.list_for_teacher(
        page=pagination.page if pagination else 1,
        page_size=pagination.page_size if pagination else 20,
        class_id=class_id,
    )
    return {
        "items": [
            {
                "id": str(a.id), "title": a.title, "description": a.description,
                "assignment_type": a.assignment_type,
                "subject_id": str(a.subject_id), "class_id": str(a.class_id),
                "due_date": a.due_date.isoformat() if a.due_date else None,
                "max_score": a.max_score, "is_published": a.is_published,
                "allow_late_submission": a.allow_late_submission,
                "created_at": a.created_at.isoformat(),
            }
            for a in assignments
        ],
        "total": total,
        "page": pagination.page if pagination else 1,
        "page_size": pagination.page_size if pagination else 20,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_assignment(payload: dict, db: DB, current_user: RequireStaff):
    svc = AssignmentService(db, current_user.school_id, current_user.id)
    try:
        assignment = await svc.create(payload)
        return {
            "id": str(assignment.id),
            "title": assignment.title,
            "due_date": assignment.due_date.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{assignment_id}/submissions")
async def get_submissions(
    assignment_id: uuid.UUID, db: DB, current_user: RequireStaff
):
    svc = AssignmentService(db, current_user.school_id, current_user.id)
    result = await svc.get_submissions(assignment_id)
    if "error" in result:
        raise HTTPException(status_code=404)
    return result


@router.post("/submissions/{submission_id}/grade")
async def grade_submission(
    submission_id: uuid.UUID,
    payload: dict,
    db: DB,
    current_user: RequireStaff,
):
    svc = AssignmentService(db, current_user.school_id, current_user.id)
    try:
        sub = await svc.grade_submission(
            submission_id,
            score=float(payload["score"]),
            comment=payload.get("comment", ""),
        )
        return {
            "id": str(sub.id),
            "score": sub.score,
            "grade": sub.grade,
            "teacher_comment": sub.teacher_comment,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
