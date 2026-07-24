"""School Management System — FastAPI Application Entry Point.

Production-grade ASGI app with middleware stack, CORS, and all v1 routers.
Auto-seeds curricula on startup. Public API at /public/v1/.
Enforces read-only mode for expired subscriptions.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger
from sqlalchemy.exc import IntegrityError

from app.api.v1 import router as v1_router
from app.api.public.router import router as public_router
from app.core.config import settings
from app.core.database import async_session_factory
from app.middleware import SchoolContextMiddleware
from app.middleware.read_only import ReadOnlyModeMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.utils.error_handlers import (
    generic_exception_handler,
    integrity_error_handler,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    logger.info(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} starting up")

    # Seed curricula and workflows on startup (idempotent — skips if exists)
    try:
        async with async_session_factory() as db:
            from app.services.curriculum.curriculum_service import seed_all_curricula
            await seed_all_curricula(db)
            await db.commit()
    except Exception as e:
        logger.warning(f"Startup seed skipped (DB may not be ready): {e}")

    yield
    logger.info("🛑 Shutting down")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="Teacher-centred school management platform for Africa.",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {"name": "Auth", "description": "Authentication & token management"},
            {"name": "Users", "description": "User CRUD"},
            {"name": "Schools", "description": "Multi-tenant school management"},
            {"name": "Students", "description": "Student profiles & promotion"},
            {"name": "Teachers", "description": "Teacher accounts & workload"},
            {"name": "Academic", "description": "Years, terms, classes, streams, subjects, departments"},
            {"name": "Timetable", "description": "Timetable with conflict detection"},
            {"name": "Attendance", "description": "Attendance recording & stats"},
            {"name": "Gradebook", "description": "Assessments, marks & grade distribution"},
            {"name": "Lessons", "description": "Lesson planning & syllabus tracking"},
            {"name": "Reports", "description": "Data exports (CSV, PDF)"},
            {"name": "Results", "description": "Report cards, rankings & PDF generation"},
            {"name": "Exams", "description": "Exam series, papers & score aggregation"},
            {"name": "Analytics", "description": "School intelligence & trends"},
            {"name": "Dashboard", "description": "Admin & teacher dashboard widgets"},
            {"name": "Billing", "description": "Subscriptions, M-Pesa, Paystack, invoices"},
            {"name": "Onboarding", "description": "Paid school setup services"},
            {"name": "Curriculum", "description": "Configurable curricula (CBC, 8-4-4, Cambridge, IB, etc.)"},
            {"name": "Workflow", "description": "Approval workflows & state machines"},
            {"name": "Audit", "description": "Comprehensive audit trail"},
            {"name": "Imports", "description": "Bulk CSV imports"},
            {"name": "Promotion", "description": "Student promotion & rollback"},
            {"name": "Notifications", "description": "Multi-channel notifications"},
            {"name": "Sync", "description": "Offline-first data synchronization"},
            {"name": "Public API", "description": "Third-party integrations & webhooks"},
        ],
    )

    # ── Middleware stack ──────────────────────────────────────────
    # 1. Security headers (lowest overhead, runs first)
    app.add_middleware(SecurityHeadersMiddleware)

    # 2. Rate limiting (blocks abusive clients early)
    app.add_middleware(RateLimitMiddleware)

    # 3. Multi-tenancy context (extracts school_id from JWT)
    app.add_middleware(SchoolContextMiddleware)

    # 4. Read-only mode (blocks writes for expired/cancelled subscriptions)
    app.add_middleware(ReadOnlyModeMiddleware)

    # 5. CORS
    cors_origins = [str(o) for o in settings.CORS_ORIGINS] if settings.CORS_ORIGINS else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False if cors_origins == ["*"] else True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 4. Compression
    app.add_middleware(GZipMiddleware, minimum_size=512)

    # ── Exception handlers ────────────────────────────────────────
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # ── Routers ───────────────────────────────────────────────────
    app.include_router(v1_router, prefix=settings.API_V1_PREFIX)
    app.include_router(public_router)

    # ── Health check ──────────────────────────────────────────────
    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "healthy", "version": settings.APP_VERSION}

    return app


app = create_app()
