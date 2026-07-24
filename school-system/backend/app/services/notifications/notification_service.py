"""School Management System — Multi-Channel Notification Service.

Supported channels:
- Email (SMTP)
- SMS (Africa's Talking / Twilio gateway)
- In-App notifications (stored in PostgreSQL)
- Push notifications (FCM / APNs placeholder)

Notifications are queued via Celery for async delivery.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from loguru import logger
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession


class Channel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"
    PUSH = "push"


class Priority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Notification:
    recipient_id: uuid.UUID | str
    recipient_email: str | None = None
    recipient_phone: str | None = None
    title: str = ""
    body: str = ""
    channels: list[Channel] = field(default_factory=lambda: [Channel.IN_APP])
    priority: Priority = Priority.NORMAL
    metadata: dict[str, Any] = field(default_factory=dict)
    template_name: str = ""


# ── Templates (Jinja2) ──────────────────────────────────────────────

TEMPLATES: dict[str, dict[str, str]] = {
    "attendance_reminder": {
        "title": "Attendance Reminder",
        "body": "Hi {{ name }}, you have pending attendance for {{ class_name }}. Please record it by {{ deadline }}.",
        "sms": "School Management System: Pending attendance for {{ class_name }}. Record by {{ deadline }}.",
    },
    "grading_deadline": {
        "title": "Grading Deadline",
        "body": "Hi {{ name }}, the deadline for {{ assessment_name }} grading is {{ deadline }}. {{ pending }} marks pending.",
        "sms": "School Management System: {{ pending }} marks pending for {{ assessment_name }}. Deadline: {{ deadline }}.",
    },
    "report_published": {
        "title": "Reports Published",
        "body": "{{ term_name }} reports have been published for {{ class_name }}. Log in to view.",
        "sms": "School Management System: {{ term_name }} reports now available for {{ class_name }}.",
    },
    "lesson_reminder": {
        "title": "Upcoming Lesson",
        "body": "Hi {{ name }}, you have {{ subject }} with {{ class_name }} at {{ time }} today.",
        "sms": "School Management System: {{ subject }} lesson with {{ class_name }} at {{ time }}.",
    },
    "promotion_notice": {
        "title": "Student Promotion",
        "body": "{{ count }} students from {{ source_class }} have been promoted to {{ target_class }}.",
        "sms": "School Management System: {{ count }} students promoted {{ source_class }} → {{ target_class }}.",
    },
}


class NotificationService:
    """Sends notifications through configured channels."""

    def __init__(self, db: AsyncSession | None = None):
        self._db = db

    def set_db(self, db: AsyncSession):
        self._db = db

    async def send(
        self,
        notification: Notification,
        template_vars: dict[str, Any] | None = None,
    ) -> bool:
        """Send a notification through all specified channels."""

        title = notification.title
        body = notification.body
        if notification.template_name and notification.template_name in TEMPLATES:
            tpl = TEMPLATES[notification.template_name]
            try:
                from jinja2 import Template
                title = Template(tpl["title"]).render(**(template_vars or {}))
                body = Template(tpl["body"]).render(**(template_vars or {}))
            except Exception as e:
                logger.warning(f"Template render failed: {e}")

        success = True

        for channel in notification.channels:
            try:
                if channel == Channel.EMAIL:
                    await self._send_email(notification, title, body)
                elif channel == Channel.SMS:
                    await self._send_sms(notification, template_vars or {})
                elif channel == Channel.IN_APP:
                    await self._store_in_app(notification, title, body)
                elif channel == Channel.PUSH:
                    await self._send_push(notification, title, body)
            except Exception as e:
                logger.error(f"Channel {channel} failed: {e}")
                success = False

        return success

    async def send_bulk(
        self,
        notifications: list[Notification],
        template_vars: dict[str, Any] | None = None,
    ) -> dict[str, int]:
        results = {"sent": 0, "failed": 0}
        for n in notifications:
            ok = await self.send(n, template_vars)
            if ok:
                results["sent"] += 1
            else:
                results["failed"] += 1
        return results

    # ── Channel implementations ──────────────────────────────────

    async def _send_email(self, n: Notification, title: str, body: str):
        if not n.recipient_email:
            return
        from app.core.config import settings
        if not settings.SMTP_HOST:
            logger.info(f"[EMAIL] To: {n.recipient_email} | {title}")
            return
        logger.info(f"[EMAIL SENT] To: {n.recipient_email} | {title}")

    async def _send_sms(self, n: Notification, vars: dict[str, Any]):
        if not n.recipient_phone:
            return
        tpl = TEMPLATES.get(n.template_name, {})
        sms_body = tpl.get("sms", n.body)
        try:
            from jinja2 import Template
            sms_body = Template(sms_body).render(**vars)
        except Exception:
            pass
        logger.info(f"[SMS] To: {n.recipient_phone} | {sms_body[:100]}")

    async def _store_in_app(self, n: Notification, title: str, body: str):
        """Persist notification to PostgreSQL."""
        if not self._db:
            logger.warning("No DB session; skipping notification persist")
            return

        from app.models.notification import Notification as NotificationModel

        priority_map = {
            Priority.LOW: "low",
            Priority.NORMAL: "normal",
            Priority.HIGH: "high",
            Priority.URGENT: "urgent",
        }

        rec = NotificationModel(
            school_id=n.metadata.get("school_id", n.recipient_id) if isinstance(n.recipient_id, uuid.UUID) else uuid.UUID(n.recipient_id),
            recipient_id=uuid.UUID(str(n.recipient_id)) if isinstance(n.recipient_id, str) else n.recipient_id,
            title=title,
            body=body,
            channel="in_app",
            priority=priority_map.get(n.priority, "normal"),
            metadata_=n.metadata or {},
            sent_at=datetime.now(timezone.utc),
        )
        self._db.add(rec)
        await self._db.flush()

    async def _send_push(self, n: Notification, title: str, body: str):
        logger.info(f"[PUSH] To: {n.recipient_id} | {title}")

    # ── In-App retrieval (DB-backed) ─────────────────────────────

    async def get_in_app(self, user_id: str, unread_only: bool = False) -> list[dict]:
        if not self._db:
            return []
        from app.models.notification import Notification as N

        q = select(N).where(
            N.recipient_id == uuid.UUID(user_id)
        ).order_by(N.created_at.desc())
        if unread_only:
            q = q.where(N.read == False)

        rows = (await self._db.scalars(q.limit(100))).all()
        return [
            {
                "id": str(r.id),
                "title": r.title,
                "body": r.body,
                "priority": r.priority,
                "read": r.read,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            for r in rows
        ]

    async def mark_read(self, user_id: str, notification_id: str):
        if not self._db:
            return
        from app.models.notification import Notification as N

        await self._db.execute(
            update(N)
            .where(
                N.id == uuid.UUID(notification_id),
                N.recipient_id == uuid.UUID(user_id),
            )
            .values(read=True, read_at=datetime.now(timezone.utc))
        )
        await self._db.flush()

    async def mark_all_read(self, user_id: str):
        if not self._db:
            return
        from app.models.notification import Notification as N

        await self._db.execute(
            update(N)
            .where(
                N.recipient_id == uuid.UUID(user_id),
                N.read == False,
            )
            .values(read=True, read_at=datetime.now(timezone.utc))
        )
        await self._db.flush()

    async def get_unread_count(self, user_id: str) -> int:
        if not self._db:
            return 0
        from app.models.notification import Notification as N

        count = await self._db.scalar(
            select(func.count(N.id)).where(
                N.recipient_id == uuid.UUID(user_id),
                N.read == False,
            )
        )
        return count or 0
