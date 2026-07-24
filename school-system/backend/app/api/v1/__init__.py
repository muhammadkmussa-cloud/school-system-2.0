"""School Management System — API v1 router aggregation (37 modules)."""

from fastapi import APIRouter

from app.api.v1 import (
    academic, advanced_dashboard, analytics, assignments, attendance,
    audit, auth, billing, calendar, curriculum, dashboard, exams,
    gradebook, health, imports, lessons, notifications, onboarding,
    platform, promotion, push, reports, results, schools, students,
    sync, teachers, timetable, users, workflow,
)
from app.api.mobile.router import router as mobile_router

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Auth"])
router.include_router(users.router, prefix="/users", tags=["Users"])
router.include_router(schools.router, prefix="/schools", tags=["Schools"])
router.include_router(students.router, prefix="/students", tags=["Students"])
router.include_router(teachers.router, prefix="/teachers", tags=["Teachers"])
router.include_router(academic.router, prefix="/academic", tags=["Academic"])
router.include_router(timetable.router, prefix="/timetable", tags=["Timetable"])
router.include_router(attendance.router, prefix="/attendance", tags=["Attendance"])
router.include_router(gradebook.router, prefix="/gradebook", tags=["Gradebook"])
router.include_router(lessons.router, prefix="/lessons", tags=["Lessons"])
router.include_router(reports.router, prefix="/reports", tags=["Reports"])
router.include_router(results.router, prefix="/results", tags=["Results"])
router.include_router(exams.router, prefix="/exams", tags=["Exams"])
router.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
router.include_router(advanced_dashboard.router, prefix="/dashboard/advanced", tags=["Advanced Dashboard"])
router.include_router(health.router, prefix="/health", tags=["System"])
router.include_router(billing.router, prefix="/billing", tags=["Billing"])
router.include_router(onboarding.router, prefix="/onboarding", tags=["Onboarding"])
router.include_router(curriculum.router, prefix="/curriculum", tags=["Curriculum"])
router.include_router(workflow.router, prefix="/workflow", tags=["Workflow"])
router.include_router(audit.router, prefix="/audit", tags=["Audit"])
router.include_router(imports.router, prefix="/imports", tags=["Imports"])
router.include_router(promotion.router, prefix="/promotion", tags=["Promotion"])
router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
router.include_router(calendar.router, prefix="/calendar", tags=["Calendar"])
router.include_router(assignments.router, prefix="/assignments", tags=["Assignments"])
router.include_router(push.router, prefix="/push", tags=["Push"])
router.include_router(sync.router, prefix="/sync", tags=["Sync"])
router.include_router(platform.router, prefix="/platform", tags=["Platform"])
router.include_router(mobile_router, tags=["Mobile"])