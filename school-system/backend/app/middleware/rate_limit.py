"""School Management System — In-memory Rate Limiting Middleware.

Simple sliding-window rate limiter per IP.  In production, replace with
a Redis-backed limiter (e.g. slowapi) for distributed consistency.

Current limits (configurable):
- Login:     5 req / 15 min window  (mitigates brute force)
- General:  120 req / 1 min window  (mitigates DoS)
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, login_limit: int = 5, login_window: int = 900,
                 general_limit: int = 120, general_window: int = 60):
        super().__init__(app)
        self.login_limit = login_limit
        self.login_window = login_window
        self.general_limit = general_limit
        self.general_window = general_window
        self._login_attempts: dict[str, list[float]] = defaultdict(list)
        self._general_attempts: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        path = request.url.path

        if path.endswith("/auth/login"):
            self._purge_old(client_ip, self._login_attempts, self.login_window)
            if len(self._login_attempts[client_ip]) >= self.login_limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many login attempts. Try again later.",
                )
            self._login_attempts[client_ip].append(now)
        else:
            self._purge_old(client_ip, self._general_attempts, self.general_window)
            if len(self._general_attempts[client_ip]) >= self.general_limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many requests. Slow down.",
                )
            self._general_attempts[client_ip].append(now)

        return await call_next(request)

    @staticmethod
    def _purge_old(key: str, store: dict, window: float):
        cutoff = time.time() - window
        store[key] = [t for t in store.get(key, []) if t > cutoff]
        if not store[key]:
            store.pop(key, None)
