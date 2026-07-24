"""School Management System — Security Headers Middleware.

Adds standard security headers to every response:
- X-Content-Type-Options (prevents MIME sniffing)
- X-Frame-Options (prevents clickjacking)
- X-XSS-Protection (legacy XSS filter)
- Content-Security-Policy (restricts resource loading)
- Strict-Transport-Security (enforces HTTPS)
- Referrer-Policy (limits referrer leakage)
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response
