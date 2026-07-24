"""School Management System — Background job definitions.

All long-running or scheduled tasks live here.

Usage:
    from app.tasks.jobs import generate_report_cards_batch
    generate_report_cards_batch.delay(school_id=str(school.id), term_id=str(term.id))
"""

from __future__ import annotations

import io
import uuid
from datetime import date, datetime, timedelta, timezone

from celery import group, shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select, func

from app.core.database import async_session_factory
from app.models.student import Student
from app.models.teacher import Teacher
from app.models.user import User
from app.models.attendance import AttendanceRecord
from app.models.assessment import Assessment, Mark

logger = get_task_logger(__name__)


async def _get_db():
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── PDF Report Cards (batch) ────────────────────────────────────────


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def generate_report_cards_batch(
    self,
    school_id: str,
    class_id: str,
    term_id: str,
) -> dict:
    """Generate PDF report cards for an entire class. Runs async."""
    import asyncio
    return asyncio.get_event_loop().run_until_complete(
        _generate_report_cards_batch_async(school_id, class_id, term_id)
    )


async def _generate_report_cards_batch_async(
    school_id: str, class_id: str, term_id: str
) -> dict:
    """Async inner function for batch PDF generation."""
    from app.services.results_engine import ResultsEngine
    from app.services.reports.pdf_report_card import generate_report_card_pdf

    sid = uuid.UUID(school_id)
    cid = uuid.UUID(class_id)
    tid = uuid.UUID(term_id)

    async with async_session_factory() as db:
        engine = ResultsEngine(db, sid)

        students = await db.scalars(
            select(Student).where(
                Student.school_id == sid,
                Student.class_id == cid,
                Student.status == "active",
            )
        )

        generated = 0
        for student in students:
            try:
                report = await engine.compute_student_report(student.id, tid)
                if report:
                    pdf_bytes = generate_report_card_pdf(report)
                    # In production: upload to S3, store URL
                    generated += 1
            except Exception as e:
                logger.error(f"Failed report for student {student.id}: {e}")

        logger.info(f"Generated {generated} report cards for class {class_id}")
        return {"generated": generated, "class_id": class_id, "term_id": term_id}


# ── Notification Dispatching ────────────────────────────────────────


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def dispatch_notification(
    self,
    recipient_id: str,
    recipient_email: str | None = None,
    recipient_phone: str | None = None,
    title: str = "",
    body: str = "",
    channels: list[str] | None = None,
    template_name: str = "",
    template_vars: dict | None = None,
):
    """Send notification through configured channels."""
    import asyncio
    return asyncio.get_event_loop().run_until_complete(
        _dispatch_notification_async(
            recipient_id, recipient_email, recipient_phone,
            title, body, channels or ["in_app"],
            template_name, template_vars,
        )
    )


async def _dispatch_notification_async(*args, **kwargs):
    from app.services.notifications.notification_service import (
        NotificationService, Notification, Channel, Priority,
    )
    async with async_session_factory() as db:
        svc = NotificationService(db)
        n = Notification(
            recipient_id=kwargs.get("recipient_id", ""),
            recipient_email=kwargs.get("recipient_email"),
            recipient_phone=kwargs.get("recipient_phone"),
            title=kwargs.get("title", ""),
            body=kwargs.get("body", ""),
            channels=[Channel(c) for c in kwargs.get("channels", ["in_app"])],
            template_name=kwargs.get("template_name", ""),
        )
        return await svc.send(n, kwargs.get("template_vars"))



# ── Scheduled Tasks ─────────────────────────────────────────────────


@shared_task
def send_attendance_reminders():
    """Daily 8 AM: remind teachers with pending attendance."""
    import asyncio
    return asyncio.get_event_loop().run_until_complete(_send_attendance_reminders_async())


async def _send_attendance_reminders_async():
    today = date.today()
    async with async_session_factory() as db:
        # Find teachers with classes today but no attendance recorded
        from app.models.timetable import TimetableEntry, Timetable
        from app.services.notifications.notification_service import NotificationService, Notification, Channel

        day = today.weekday()
        # Get all active teachers
        teachers = await db.scalars(
            select(Teacher).where(Teacher.is_active == True)
        )

        svc = NotificationService(db)
        sent = 0
        for teacher in teachers:
            # Check if they have classes today
            entries = await db.scalars(
                select(TimetableEntry).where(
                    TimetableEntry.teacher_id == teacher.id,
                    TimetableEntry.day_of_week == day,
                )
            )
            entries_list = list(entries)

            if not entries_list:
                continue

            # Check for pending attendance
            has_pending = False
            for entry in entries_list:
                existing = await db.scalar(
                    select(func.count(AttendanceRecord.id)).where(
                        AttendanceRecord.class_id == entry.class_id,
                        AttendanceRecord.attendance_date == today,
                    )
                )
                if not existing:
                    has_pending = True
                    break

            if has_pending and teacher.user_id:
                await svc.send(Notification(
                    recipient_id=str(teacher.user_id),
                    title="📋 Attendance Reminder",
                    body=f"You have pending attendance for today ({today}). Please record it by 4 PM.",
                    channels=[Channel.IN_APP],
                ))
                sent += 1

        logger.info(f"Sent {sent} attendance reminders")
        return {"reminders_sent": sent}


@shared_task
def check_grading_deadlines():
    """Weekly Monday check: remind about pending grading."""
    import asyncio
    return asyncio.get_event_loop().run_until_complete(_check_grading_deadlines_async())


async def _check_grading_deadlines_async():
    async with async_session_factory() as db:
        from app.services.notifications.notification_service import NotificationService, Notification, Channel

        # Find assessments with no marks yet
        assessments = await db.scalars(
            select(Assessment).where(
                Assessment.created_at >= datetime.now(timezone.utc) - timedelta(days=14),
            )
        )

        svc = NotificationService(db)
        sent = 0
        for a in assessments:
            mark_count = await db.scalar(
                select(func.count(Mark.id)).where(Mark.assessment_id == a.id)
            )
            if not mark_count:
                teacher = await db.scalar(select(Teacher).where(Teacher.id == a.teacher_id))
                if teacher and teacher.user_id:
                    await svc.send(Notification(
                        recipient_id=str(teacher.user_id),
                        title="📝 Grading Reminder",
                        body=f"No marks recorded yet for '{a.name}'. Please complete grading.",
                        channels=[Channel.IN_APP],
                    ))
                    sent += 1

        logger.info(f"Sent {sent} grading deadline reminders")
        return {"reminders_sent": sent}


@shared_task
def cleanup_old_sync_records():
    """Weekly: mark old sync records as resolved."""
    import asyncio
    return asyncio.get_event_loop().run_until_complete(_cleanup_old_sync_records_async())


async def _cleanup_old_sync_records_async():
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    async with async_session_factory() as db:
        # Mark old unsynced records as synced (they're too old to sync)
        from sqlalchemy import update as sql_update

        result_att = await db.execute(
            sql_update(AttendanceRecord)
            .where(
                AttendanceRecord.synced == False,
                AttendanceRecord.updated_at < cutoff,
            )
            .values(synced=True)
        )
        result_mark = await db.execute(
            sql_update(Mark)
            .where(
                Mark.synced == False,
                Mark.updated_at < cutoff,
            )
            .values(synced=True)
        )

        logger.info(f"Cleaned up {result_att.rowcount} attendance + {result_mark.rowcount} marks sync records")
        return {"attendance_cleaned": result_att.rowcount, "marks_cleaned": result_mark.rowcount}


@shared_task
def daily_health_check():
    """Daily system health check — logs key metrics."""
    import asyncio
    return asyncio.get_event_loop().run_until_complete(_daily_health_check_async())


async def _daily_health_check_async():
    async with async_session_factory() as db:
        total_schools = await db.scalar(select(func.count("schools.id")))
        total_students = await db.scalar(select(func.count(Student.id)))
        total_teachers = await db.scalar(select(func.count(Teacher.id)))

        logger.info(
            f"📊 Daily Health: {total_schools} schools, "
            f"{total_students} students, {total_teachers} teachers"
        )
        return {
            "schools": total_schools or 0,
            "students": total_students or 0,
            "teachers": total_teachers or 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
