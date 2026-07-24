"""Notification API — send, retrieve, mark as read."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentUser, DB
from app.services.notifications.notification_service import (
    NotificationService,
    Notification,
    Channel,
    Priority,
)

router = APIRouter()


@router.get("")
async def get_notifications(
    db: DB,
    current_user: CurrentUser,
    unread_only: bool = Query(False),
):
    """Get in-app notifications for the current user."""
    svc = NotificationService(db)
    notifications = await svc.get_in_app(str(current_user.id), unread_only=unread_only)
    return {"notifications": notifications, "unread_count": await svc.get_unread_count(str(current_user.id))}


@router.post("/{notification_id}/read")
async def mark_read(notification_id: str, db: DB, current_user: CurrentUser):
    svc = NotificationService(db)
    await svc.mark_read(str(current_user.id), notification_id)
    return {"ok": True}


@router.post("/read-all")
async def mark_all_read(db: DB, current_user: CurrentUser):
    svc = NotificationService(db)
    await svc.mark_all_read(str(current_user.id))
    return {"ok": True}


@router.get("/unread-count")
async def unread_count(db: DB, current_user: CurrentUser):
    svc = NotificationService(db)
    count = await svc.get_unread_count(str(current_user.id))
    return {"count": count}


@router.post("/send")
async def send_notification(payload: dict, current_user: CurrentUser, db: DB):
    """Send a notification (for testing/admin use)."""
    n = Notification(
        recipient_id=payload.get("recipient_id", str(current_user.id)),
        recipient_email=payload.get("recipient_email"),
        recipient_phone=payload.get("recipient_phone"),
        title=payload.get("title", "Notification"),
        body=payload.get("body", ""),
        channels=[Channel(c) for c in payload.get("channels", ["in_app"])],
        priority=Priority(payload.get("priority", "normal")),
        template_name=payload.get("template_name", ""),
    )
    svc = NotificationService(db)
    ok = await svc.send(n, payload.get("template_vars"))
    return {"sent": ok}
