"""Push notification registration & sending API."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DB
from app.services.notifications.push_service import PushNotificationService, PushMessage

router = APIRouter()
push_svc = PushNotificationService()


@router.post("/register")
async def register_device(payload: dict, current_user: CurrentUser):
    """Register a device for push notifications."""
    token = payload.get("token")
    platform = payload.get("platform", "unknown")

    if not token:
        return {"error": "token required"}

    await push_svc.register_device(current_user.id, token, platform)
    count = await push_svc.get_registered_count(current_user.id)
    return {"registered": True, "device_count": count}


@router.post("/unregister")
async def unregister_device(payload: dict, current_user: CurrentUser):
    await push_svc.unregister_device(current_user.id, payload.get("token", ""))
    return {"unregistered": True}


@router.get("/status")
async def push_status(current_user: CurrentUser):
    count = await push_svc.get_registered_count(current_user.id)
    return {"devices_registered": count}


@router.post("/send", status_code=status.HTTP_200_OK)
async def send_test_push(payload: dict, current_user: CurrentUser):
    """Send a test push notification (admin use)."""
    msg = PushMessage(
        title=payload.get("title", "School Management System"),
        body=payload.get("body", "Test notification"),
        data=payload.get("data"),
    )
    result = await push_svc.send_to_user(current_user.id, msg)
    return result
