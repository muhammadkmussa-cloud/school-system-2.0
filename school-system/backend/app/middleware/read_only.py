"""School Management System — Read-Only Mode Middleware.

Enforces the trial/expired read-only policy at the HTTP level.

When a school's subscription is expired:
    GET  → allowed (view reports, see data)
    POST/PUT/PATCH/DELETE → blocked with 402 Payment Required

Exceptions: billing endpoints, auth, and health checks always work.
This ensures schools never lose access to their data even when expired.
"""

from __future__ import annotations

import uuid

from fastapi import Request, HTTPException, status
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.database import async_session_factory
from app.core.trial_lifecycle import (
    compute_subscription_state,
    is_write_method,
    is_always_allowed,
    SubscriptionStatus,
)
from app.models.billing import SchoolSubscription


class ReadOnlyModeMiddleware(BaseHTTPMiddleware):
    """Intercepts writes for schools in read-only mode.

    Must be placed AFTER SchoolContextMiddleware so request.state.school_id is set.
    """

    async def dispatch(self, request: Request, call_next):
        # Skip non-API paths
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)

        method = request.method

        # Always-allow list (auth, billing, health)
        if is_always_allowed(method, path):
            return await call_next(request)

        # Only block write methods
        if not is_write_method(method):
            return await call_next(request)

        # Get school_id from request state (set by SchoolContextMiddleware)
        school_id_str = getattr(request.state, "school_id", None)
        if not school_id_str:
            return await call_next(request)

        # Check subscription state
        try:
            school_id = uuid.UUID(school_id_str)
        except (ValueError, TypeError):
            return await call_next(request)

        effective_status = await self._get_school_effective_status(school_id)

        if effective_status == "read_only":
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "subscription_expired",
                    "message": (
                        "Your account is in read-only mode. All data is safe and "
                        "viewable, but new records cannot be created. Please "
                        "subscribe to restore full access."
                    ),
                    "action": "subscribe",
                    "billing_url": "/api/v1/billing/subscription",
                },
            )

        return await call_next(request)

    async def _get_school_effective_status(self, school_id: uuid.UUID) -> str:
        """Check subscription state and return effective_status."""
        try:
            async with async_session_factory() as db:
                sub = await db.scalar(
                    select(SchoolSubscription).where(
                        SchoolSubscription.school_id == school_id,
                    )
                )
                if not sub:
                    # No subscription row → allow writes (free tier)
                    return "active"

                state = compute_subscription_state(sub)
                return state["effective_status"]
        except Exception:
            # If DB is down, let the request through (fail at the route level)
            return "active"
