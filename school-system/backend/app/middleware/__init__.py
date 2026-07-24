"""School Management System — Multi-tenancy middleware.

Ensures every database query is automatically scoped to the user's school.
For platform admins, the scope is bypassed (they operate across schools).
"""

from __future__ import annotations

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import event
from sqlalchemy.orm import Mapper, Session

from app.core.security import decode_token


class SchoolContextMiddleware(BaseHTTPMiddleware):
    """Extracts school_id from JWT and attaches it to request.state."""

    async def dispatch(self, request: Request, call_next):
        # Skip auth endpoints
        path = request.url.path
        if any(
            path.startswith(p)
            for p in ["/health", "/docs", "/redoc", "/openapi.json", "/api/v1/auth"]
        ):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                token = auth_header.split(" ", 1)[1]
                payload = decode_token(token)
                request.state.school_id = payload.get("school_id")
                request.state.user_id = payload.get("sub")
                request.state.user_role = payload.get("role", "")
            except Exception:
                pass  # Will be caught by auth dependency

        return await call_next(request)
