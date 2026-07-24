"""Workflow API — manage approval chains."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query

from app.core.dependencies import CurrentUser, DB, RequireStaff
from app.services.workflow.workflow_engine import WorkflowEngine

router = APIRouter()


@router.get("/definitions")
async def list_workflows(db: DB, current_user: RequireStaff):
    """List all workflow definitions for this school."""
    from sqlalchemy import select
    from app.models.workflow import WorkflowDefinition

    rows = await db.scalars(
        select(WorkflowDefinition).where(
            WorkflowDefinition.school_id == current_user.school_id,
            WorkflowDefinition.is_active == True,
        )
    )
    return [
        {
            "id": str(wf.id), "name": wf.name, "entity_type": wf.entity_type,
            "description": wf.description,
        }
        for wf in rows
    ]


@router.get("/definitions/{workflow_id}")
async def get_workflow(workflow_id: uuid.UUID, db: DB, current_user: RequireStaff):
    """Get workflow states and transitions."""
    from sqlalchemy import select
    from app.models.workflow import WorkflowDefinition, WorkflowState

    wf = await db.scalar(
        select(WorkflowDefinition).where(
            WorkflowDefinition.id == workflow_id,
            WorkflowDefinition.school_id == current_user.school_id,
        )
    )
    if not wf:
        raise HTTPException(status_code=404)

    states = await db.scalars(
        select(WorkflowState).where(WorkflowState.workflow_id == wf.id).order_by(WorkflowState.sort_order)
    )
    return {
        "id": str(wf.id),
        "name": wf.name,
        "entity_type": wf.entity_type,
        "states": [
            {
                "name": s.name, "display": s.display_name,
                "order": s.sort_order, "required_role": s.required_role,
                "is_final": s.is_final, "color": s.color,
            }
            for s in states
        ],
    }


@router.post("/instances/{instance_id}/transition")
async def execute_transition(
    instance_id: uuid.UUID,
    db: DB,
    current_user: RequireStaff,
    action: str = Query(...),
    comment: str = Query(""),
):
    """Execute a workflow transition (approve, reject, submit, etc.)."""
    engine = WorkflowEngine(db, current_user.school_id)

    try:
        instance = await engine.transition(
            instance_id=instance_id,
            action_name=action,
            actor_id=current_user.id,
            actor_role=current_user.role,
            comment=comment or None,
        )
        return {
            "id": str(instance.id),
            "entity_id": instance.entity_id,
            "current_state": instance.current_state,
            "completed": instance.completed_at is not None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.get("/instances/{instance_id}/actions")
async def available_actions(
    instance_id: uuid.UUID,
    db: DB,
    current_user: RequireStaff,
):
    """What actions can the current user take?"""
    engine = WorkflowEngine(db, current_user.school_id)
    actions = await engine.get_available_actions(instance_id, current_user.role)
    return {"actions": actions}


@router.get("/instances/{instance_id}/history")
async def workflow_history(instance_id: uuid.UUID, db: DB, current_user: RequireStaff):
    """Get the history of a workflow instance."""
    engine = WorkflowEngine(db, current_user.school_id)
    history = await engine.get_history(instance_id)
    return {
        "history": [
            {
                "from_state": h.from_state, "to_state": h.to_state,
                "action": h.action, "comment": h.comment,
                "actor_id": str(h.actor_id),
                "created_at": h.created_at.isoformat(),
            }
            for h in history
        ],
    }
