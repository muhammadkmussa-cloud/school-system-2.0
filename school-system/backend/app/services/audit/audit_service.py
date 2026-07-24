"""School Management System — Audit Logging Service.

Lightweight, non-blocking audit trail. Every mutation can be logged.
Designed for answering:
- Who changed this mark?
- Who deleted that attendance record?
- When was this report generated?
- What was the old value before the change?
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.audit import AuditLog


class AuditService:
    """Central audit trail. Use as a FastAPI dependency or direct service."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        *,
        school_id: uuid.UUID,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        actor_id: uuid.UUID | None = None,
        actor_role: str | None = None,
        actor_name: str | None = None,
        changes: dict[str, Any] | None = None,
        summary: str | None = None,
        ip_address: str | None = None,
        endpoint: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> AuditLog:
        """Record an audit entry. Returns the created log."""

        # Auto-generate summary from changes if not provided
        if not summary and changes:
            parts = []
            for field, delta in changes.items():
                old = delta.get("old", "—")
                new = delta.get("new", "—")
                parts.append(f"{field}: {old} → {new}")
            summary = "; ".join(parts)

        entry = AuditLog(
            school_id=school_id,
            actor_id=actor_id,
            actor_role=actor_role,
            actor_name=actor_name,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            changes=changes,
            summary=summary,
            ip_address=ip_address,
            endpoint=endpoint,
            user_agent=user_agent,
            request_id=request_id,
        )
        self.db.add(entry)

        # Non-blocking: flush but don't commit here (caller commits)
        try:
            await self.db.flush()
        except Exception as e:
            logger.error(f"Audit log write failed (non-fatal): {e}")

        return entry

    # ── Convenience wrappers ─────────────────────────────────────

    async def log_create(
        self, school_id: uuid.UUID, entity_type: str, entity_id: str,
        actor: Any, data: dict, **ctx,
    ) -> AuditLog:
        return await self.log(
            school_id=school_id, action="create", entity_type=entity_type,
            entity_id=entity_id,
            actor_id=getattr(actor, "id", None),
            actor_role=getattr(actor, "role", None),
            actor_name=getattr(actor, "full_name", None),
            changes={k: {"old": None, "new": v} for k, v in data.items()},
            summary=f"Created {entity_type} {entity_id[:8]}",
            **ctx,
        )

    async def log_update(
        self, school_id: uuid.UUID, entity_type: str, entity_id: str,
        actor: Any, old_data: dict, new_data: dict, **ctx,
    ) -> AuditLog:
        changes = {}
        for key in set(old_data) | set(new_data):
            old_val = old_data.get(key)
            new_val = new_data.get(key)
            if old_val != new_val:
                changes[key] = {"old": old_val, "new": new_val}

        if not changes:
            return None  # nothing changed

        return await self.log(
            school_id=school_id, action="update", entity_type=entity_type,
            entity_id=entity_id,
            actor_id=getattr(actor, "id", None),
            actor_role=getattr(actor, "role", None),
            actor_name=getattr(actor, "full_name", None),
            changes=changes,
            **ctx,
        )

    async def log_delete(
        self, school_id: uuid.UUID, entity_type: str, entity_id: str,
        actor: Any, deleted_data: dict, **ctx,
    ) -> AuditLog:
        return await self.log(
            school_id=school_id, action="delete", entity_type=entity_type,
            entity_id=entity_id,
            actor_id=getattr(actor, "id", None),
            actor_role=getattr(actor, "role", None),
            actor_name=getattr(actor, "full_name", None),
            changes={k: {"old": v, "new": None} for k, v in deleted_data.items()},
            summary=f"Deleted {entity_type} {entity_id[:8]}",
            **ctx,
        )

    # ── Queries ──────────────────────────────────────────────────

    async def query(
        self,
        school_id: uuid.UUID,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        action: str | None = None,
        actor_id: uuid.UUID | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditLog], int]:
        """Search the audit trail with filters."""
        stmt = select(AuditLog).where(AuditLog.school_id == school_id)
        count_q = select(func.count(AuditLog.id)).where(AuditLog.school_id == school_id)

        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
            count_q = count_q.where(AuditLog.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(AuditLog.entity_id == entity_id)
            count_q = count_q.where(AuditLog.entity_id == entity_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
            count_q = count_q.where(AuditLog.action == action)
        if actor_id:
            stmt = stmt.where(AuditLog.actor_id == actor_id)
            count_q = count_q.where(AuditLog.actor_id == actor_id)
        if since:
            stmt = stmt.where(AuditLog.created_at >= since)
            count_q = count_q.where(AuditLog.created_at >= since)
        if until:
            stmt = stmt.where(AuditLog.created_at <= until)
            count_q = count_q.where(AuditLog.created_at <= until)

        total = await self.db.scalar(count_q)
        rows = (await self.db.scalars(
            stmt.order_by(AuditLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )).all()

        return list(rows), total or 0

    async def get_entity_history(
        self, school_id: uuid.UUID, entity_type: str, entity_id: str
    ) -> list[AuditLog]:
        """Full audit trail for a single entity."""
        rows = await self.db.scalars(
            select(AuditLog)
            .where(
                AuditLog.school_id == school_id,
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == entity_id,
            )
            .order_by(AuditLog.created_at.desc())
            .limit(settings.AUDIT_RECENT_LIMIT)
        )
        return list(rows)
