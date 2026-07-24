"""School Management System — Workflow & Approval models.

Configurable state machines for:
- Report card approval chain (teacher → head → principal → published)
- Exam result publishing
- Student promotion approval
- Attendance period locking

Each workflow has states, transitions, and role-based approvers.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime, ForeignKey, Integer, String, Text, JSON, Boolean, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class WorkflowDefinition(Base, TimestampMixin):
    """A named workflow template (e.g. 'Report Card Approval')."""
    __tablename__ = "workflow_definitions"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "report_card", "exam_result", "promotion", "attendance_lock"
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[dict | None] = mapped_column(JSON)

    states = relationship("WorkflowState", back_populates="workflow", lazy="dynamic",
                          cascade="all, delete-orphan")
    instances = relationship("WorkflowInstance", back_populates="workflow", lazy="dynamic")


class WorkflowState(Base, TimestampMixin):
    """A state in a workflow with role-based approver config."""
    __tablename__ = "workflow_states"
    __table_args__ = (
        UniqueConstraint("workflow_id", "name", name="uq_workflow_state_name"),
    )

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # "draft", "pending_review"
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    required_role: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # role that can approve at this state
    is_final: Mapped[bool] = mapped_column(Boolean, default=False)
    color: Mapped[str | None] = mapped_column(String(20))  # hex for UI

    workflow = relationship("WorkflowDefinition", back_populates="states")
    transitions_from = relationship(
        "WorkflowTransition", back_populates="from_state", lazy="dynamic",
        foreign_keys="WorkflowTransition.from_state_id",
    )


class WorkflowTransition(Base, TimestampMixin):
    """An allowed transition from state A → B with an action name."""
    __tablename__ = "workflow_transitions"

    from_state_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_states.id", ondelete="CASCADE"), nullable=False
    )
    to_state_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_states.id", ondelete="CASCADE"), nullable=False
    )
    action_name: Mapped[str] = mapped_column(String(100), nullable=False)  # "approve", "reject", "submit"
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)

    from_state = relationship("WorkflowState", back_populates="transitions_from",
                              foreign_keys=[from_state_id])


class WorkflowInstance(Base, TimestampMixin):
    """A concrete workflow run for a specific entity."""
    __tablename__ = "workflow_instances"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)  # UUID of the entity
    current_state: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSON)  # snapshot of entity at workflow start
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    workflow = relationship("WorkflowDefinition", back_populates="instances")
    history = relationship("WorkflowAction", back_populates="instance", lazy="dynamic",
                           order_by="WorkflowAction.created_at")


class WorkflowAction(Base, TimestampMixin):
    """A single action taken on a workflow instance."""
    __tablename__ = "workflow_actions"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_instances.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=False
    )
    from_state: Mapped[str] = mapped_column(String(100), nullable=False)
    to_state: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # "approve", "reject"
    comment: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict | None] = mapped_column(JSON, name="metadata")

    instance = relationship("WorkflowInstance", back_populates="history")
