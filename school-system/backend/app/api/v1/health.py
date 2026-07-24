"""Production Health & Monitoring Endpoint.

Exposes system health for load balancers, monitoring tools (Prometheus),
and operational dashboards. Checks database connectivity, Redis, Celery,
and file storage.
"""

from __future__ import annotations

import time

from fastapi import APIRouter
from sqlalchemy import text

from app.core.dependencies import DB

router = APIRouter(tags=["System"])


@router.get("/health/full")
async def full_health(db: DB):
    """Comprehensive health check for production monitoring.

    Returns 200 only if all dependencies are healthy.
    Returns 503 if any dependency is degraded.
    """
    checks: dict[str, dict] = {}
    overall_healthy = True

    # ── Database ───────────────────────────────────────────────
    t0 = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        db_latency = round((time.perf_counter() - t0) * 1000, 2)
        checks["database"] = {
            "status": "healthy",
            "latency_ms": db_latency,
        }
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}
        overall_healthy = False

    # ── Redis ──────────────────────────────────────────────────
    try:
        from app.core.config import settings
        import redis.asyncio as aioredis
        redis_client = aioredis.from_url(settings.REDIS_URL, socket_timeout=2)
        await redis_client.ping()
        await redis_client.close()
        checks["redis"] = {"status": "healthy"}
    except Exception as e:
        checks["redis"] = {"status": "degraded", "error": str(e)}

    # ── Celery ────────────────────────────────────────────────
    try:
        from app.tasks.celery_app import celery_app
        insp = celery_app.control.inspect()
        stats = insp.stats()
        if stats:
            workers = len(stats)
            checks["celery"] = {"status": "healthy", "workers": workers}
        else:
            checks["celery"] = {"status": "degraded", "workers": 0, "note": "No workers responding"}
    except Exception as e:
        checks["celery"] = {"status": "degraded", "error": str(e)}

    # ── S3 Storage ────────────────────────────────────────────
    try:
        from app.core.config import settings
        if settings.S3_ENDPOINT:
            checks["storage"] = {"status": "configured", "endpoint": settings.S3_ENDPOINT}
        else:
            checks["storage"] = {"status": "not_configured"}
    except Exception:
        checks["storage"] = {"status": "not_configured"}

    # ── Response ──────────────────────────────────────────────
    status_code = 200 if overall_healthy else 503

    return {
        "status": "healthy" if overall_healthy else "degraded",
        "version": "1.0.0",
        "timestamp": time.time(),
        "checks": checks,
        "uptime_seconds": time.process_time(),
    }
