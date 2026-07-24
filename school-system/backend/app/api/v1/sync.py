"""Offline sync API — client push/pull changes."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DB
from app.services.sync.sync_service import SyncService, SyncChange, SyncEntity, SyncAction

router = APIRouter()


@router.post("/push")
async def push_changes(
    payload: dict,
    db: DB,
    current_user: CurrentUser,
):
    """Accept client-side offline changes and merge them."""
    raw_changes = payload.get("changes", [])
    last_sync_at = payload.get("last_sync_at")

    changes = [
        SyncChange(
            entity=SyncEntity(c["entity"]),
            action=SyncAction(c.get("action", "update")),
            payload=c["payload"],
            client_timestamp=c["client_timestamp"],
            client_id=c.get("client_id", "unknown"),
            change_id=c.get("change_id", ""),
        )
        for c in raw_changes
    ]

    svc = SyncService(db, current_user.school_id, current_user.id)
    result = await svc.synchronize(changes, last_sync_at)

    return {
        "applied": result.applied,
        "conflicts": result.conflicts,
        "errors": result.errors,
        "server_changes": result.server_changes,
    }


@router.get("/status")
async def sync_status(db: DB, current_user: CurrentUser):
    """Get pending sync counts."""
    svc = SyncService(db, current_user.school_id, current_user.id)
    return await svc.get_sync_status()
