"""School Management System — Celery application factory."""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "school_system",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.jobs"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Nairobi",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes max
    task_soft_time_limit=25 * 60,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=200,
)

# ── Scheduled beat ──────────────────────────────────────────────────
celery_app.conf.beat_schedule = {
    "attendance-reminder-daily": {
        "task": "app.tasks.jobs.send_attendance_reminders",
        "schedule": crontab(hour=8, minute=0),  # 8:00 AM EAT daily
    },
    "grading-deadline-check": {
        "task": "app.tasks.jobs.check_grading_deadlines",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),  # Monday 9 AM
    },
    "sync-cleanup": {
        "task": "app.tasks.jobs.cleanup_old_sync_records",
        "schedule": crontab(hour=3, minute=0, day_of_week=6),  # Saturday 3 AM
    },
    "backup-health-check": {
        "task": "app.tasks.jobs.daily_health_check",
        "schedule": crontab(hour=7, minute=0),  # 7:00 AM daily
    },
}
