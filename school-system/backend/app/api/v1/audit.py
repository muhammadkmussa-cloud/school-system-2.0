"""Audit log API — query the audit trail."""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DB, RequireSchoolAdmin
from app.services.audit.audit_service import AuditService

router = APIRouter()


@router.get("")
async def query_audit_logs(
    db: DB,
    current_user: RequireSchoolAdmin,
    entity_type: str = "",
    entity_id: str = "",
    action: str = "",
    actor_id: str = "",
    since: str = "",
    until: str = "",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Search the audit trail with filters."""
    svc = AuditService(db)
    logs, total = await svc.query(
        school_id=current_user.school_id,
        entity_type=entity_type or None,
        entity_id=entity_id or None,
        action=action or None,
        actor_id=uuid.UUID(actor_id) if actor_id else None,
        since=datetime.fromisoformat(since) if since else None,
        until=datetime.fromisoformat(until) if until else None,
        page=page,
        page_size=page_size,
    )
    return {
        "logs": [
            {
                "id": str(l.id),
                "action": l.action,
                "entity_type": l.entity_type,
                "entity_id": l.entity_id,
                "actor_name": l.actor_name,
                "actor_role": l.actor_role,
                "summary": l.summary,
                "changes": l.changes,
                "ip_address": l.ip_address,
                "endpoint": l.endpoint,
                "created_at": l.created_at.isoformat(),
            }
            for l in logs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/entity/{entity_type}/{entity_id}")
async def entity_history(
    entity_type: str,
    entity_id: str,
    db: DB,
    current_user: RequireSchoolAdmin,
):
    """Get the full audit trail for a specific entity."""
    svc = AuditService(db)
    logs = await svc.get_entity_history(current_user.school_id, entity_type, entity_id)
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "history": [
            {
                "id": str(l.id),
                "action": l.action,
                "actor_name": l.actor_name,
                "summary": l.summary,
                "changes": l.changes,
                "created_at": l.created_at.isoformat(),
            }
            for l in logs
        ],
    }
