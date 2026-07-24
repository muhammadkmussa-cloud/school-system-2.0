"""School Management System — Audit log models.

Tracks every mutation in the system with:
- Who did it
- What changed (old → new)
- When it happened
- Where (IP, endpoint)
- Why (action context)
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    """Immutable audit trail entry for every state change."""
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    actor_role: Mapped[str | None] = mapped_column(String(50))
    actor_name: Mapped[str | None] = mapped_column(String(200))

    # What happened
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # "create", "update", "delete", "login", "logout", "export", "approve", "reject"

    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # "student", "mark", "attendance", "report"
    entity_id: Mapped[str | None] = mapped_column(String(100), index=True)

    # Change details
    changes: Mapped[dict | None] = mapped_column(JSON)  # {"field": {"old": ..., "new": ...}}
    summary: Mapped[str | None] = mapped_column(Text)  # human-readable summary

    # Context
    ip_address: Mapped[str | None] = mapped_column(String(45))
    endpoint: Mapped[str | None] = mapped_column(String(500))
    user_agent: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action}:{self.entity_type} by {self.actor_name}>"
