"""School Management System — Workflow Engine.

Executes state-machine workflows. Schools can configure custom approval chains.
Built-in templates for common education workflows.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow import (
    WorkflowDefinition,
    WorkflowState,
    WorkflowTransition,
    WorkflowInstance,
    WorkflowAction,
)

# ── Built-in workflow templates ────────────────────────────────────

BUILTIN_WORKFLOWS = {
    "report_card": {
        "name": "Report Card Approval",
        "entity_type": "report_card",
        "states": [
            ("draft", "Draft", 1, "teacher", False, "#6b7280"),
            ("pending_head", "Pending Head Teacher", 2, "head_teacher", False, "#f59e0b"),
            ("pending_principal", "Pending Principal", 3, "deputy_principal", False, "#f59e0b"),
            ("approved", "Approved", 4, "school_admin", False, "#3b82f6"),
            ("published", "Published", 5, "school_admin", True, "#10b981"),
        ],
        "transitions": [
            ("draft", "pending_head", "submit", "Submit for Review"),
            ("pending_head", "pending_principal", "approve", "Approve"),
            ("pending_head", "draft", "reject", "Return for Revision"),
            ("pending_principal", "approved", "approve", "Approve"),
            ("pending_principal", "draft", "reject", "Return for Revision"),
            ("approved", "published", "publish", "Publish to Parents"),
            ("approved", "draft", "unpublish", "Unpublish"),
        ],
    },
    "exam_publishing": {
        "name": "Exam Result Publishing",
        "entity_type": "exam_result",
        "states": [
            ("draft", "Draft", 1, "teacher", False, "#6b7280"),
            ("pending_moderation", "Pending Moderation", 2, "head_teacher", False, "#f59e0b"),
            ("moderated", "Moderated", 3, "deputy_principal", False, "#8b5cf6"),
            ("published", "Published", 4, "school_admin", True, "#10b981"),
        ],
        "transitions": [
            ("draft", "pending_moderation", "submit", "Submit for Moderation"),
            ("pending_moderation", "moderated", "approve", "Approve After Moderation"),
            ("pending_moderation", "draft", "reject", "Return for Correction"),
            ("moderated", "published", "publish", "Publish Results"),
            ("moderated", "draft", "reject", "Reject"),
        ],
    },
    "promotion": {
        "name": "Student Promotion Approval",
        "entity_type": "promotion",
        "states": [
            ("proposed", "Proposed", 1, "head_teacher", False, "#f59e0b"),
            ("pending_approval", "Pending Approval", 2, "deputy_principal", False, "#3b82f6"),
            ("approved", "Approved", 3, "school_admin", True, "#10b981"),
            ("rejected", "Rejected", 4, "school_admin", True, "#ef4444"),
        ],
        "transitions": [
            ("proposed", "pending_approval", "submit", "Submit Promotion List"),
            ("pending_approval", "approved", "approve", "Approve Promotion"),
            ("pending_approval", "rejected", "reject", "Reject Promotion"),
        ],
    },
    "attendance_lock": {
        "name": "Attendance Period Lock",
        "entity_type": "attendance_period",
        "states": [
            ("open", "Open for Recording", 1, "teacher", False, "#10b981"),
            ("locked", "Locked", 2, "school_admin", True, "#6b7280"),
        ],
        "transitions": [
            ("open", "locked", "lock", "Lock Period"),
        ],
    },
}


class WorkflowEngine:
    """Configurable state machine for education workflows."""

    def __init__(self, db: AsyncSession, school_id: uuid.UUID):
        self.db = db
        self.school_id = school_id

    # ── Setup ────────────────────────────────────────────────────

    async def ensure_builtin_workflows(self) -> int:
        """Create default workflows if they don't exist. Returns count created."""
        count = 0
        for key, template in BUILTIN_WORKFLOWS.items():
            exists = await self.db.scalar(
                select(WorkflowDefinition).where(
                    WorkflowDefinition.school_id == self.school_id,
                    WorkflowDefinition.entity_type == template["entity_type"],
                )
            )
            if exists:
                continue

            wf = WorkflowDefinition(
                school_id=self.school_id,
                name=template["name"],
                entity_type=template["entity_type"],
                is_active=True,
            )
            self.db.add(wf)
            await self.db.flush()

            # Create states
            state_map: dict[str, uuid.UUID] = {}
            for name, display, order, role, final, color in template["states"]:
                st = WorkflowState(
                    workflow_id=wf.id,
                    name=name,
                    display_name=display,
                    sort_order=order,
                    required_role=role,
                    is_final=final,
                    color=color,
                )
                self.db.add(st)
                await self.db.flush()
                state_map[name] = st.id

            # Create transitions
            for from_name, to_name, action, display in template["transitions"]:
                self.db.add(WorkflowTransition(
                    from_state_id=state_map[from_name],
                    to_state_id=state_map[to_name],
                    action_name=action,
                    display_name=display,
                ))

            count += 1

        await self.db.flush()
        return count

    # ── Instance management ──────────────────────────────────────

    async def start_workflow(
        self,
        entity_type: str,
        entity_id: str,
        payload: dict[str, Any] | None = None,
    ) -> WorkflowInstance | None:
        """Begin a new workflow for an entity."""
        wf = await self.db.scalar(
            select(WorkflowDefinition).where(
                WorkflowDefinition.school_id == self.school_id,
                WorkflowDefinition.entity_type == entity_type,
                WorkflowDefinition.is_active == True,
            )
        )
        if not wf:
            logger.warning(f"No active workflow for {entity_type} in school {self.school_id}")
            return None

        # Find initial state (sort_order=1)
        init_state = await self.db.scalar(
            select(WorkflowState).where(
                WorkflowState.workflow_id == wf.id,
                WorkflowState.sort_order == 1,
            )
        )
        if not init_state:
            return None

        instance = WorkflowInstance(
            workflow_id=wf.id,
            entity_id=entity_id,
            current_state=init_state.name,
            payload=payload or {},
        )
        self.db.add(instance)
        await self.db.flush()

        # Log initial action
        self.db.add(WorkflowAction(
            instance_id=instance.id,
            actor_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),  # system
            from_state="__start__",
            to_state=init_state.name,
            action="start",
            comment="Workflow started",
        ))
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def transition(
        self,
        instance_id: uuid.UUID,
        action_name: str,
        actor_id: uuid.UUID,
        actor_role: str,
        comment: str | None = None,
    ) -> WorkflowInstance:
        """Execute a transition if the actor has permission."""

        instance = await self.db.scalar(
            select(WorkflowInstance).where(WorkflowInstance.id == instance_id)
        )
        if not instance:
            raise ValueError("Workflow instance not found")
        if instance.completed_at:
            raise ValueError("Workflow already completed")

        wf = await self.db.scalar(
            select(WorkflowDefinition).where(WorkflowDefinition.id == instance.workflow_id)
        )

        # Find current state
        current_state = await self.db.scalar(
            select(WorkflowState).where(
                WorkflowState.workflow_id == wf.id,
                WorkflowState.name == instance.current_state,
            )
        )
        if not current_state:
            raise ValueError(f"Unknown state: {instance.current_state}")

        # Check actor role matches required_role for current state
        if actor_role != current_state.required_role and actor_role != "school_admin" and actor_role != "platform_admin":
            raise PermissionError(
                f"Role '{actor_role}' cannot approve. Required: '{current_state.required_role}'"
            )

        # Find transition
        transition = await self.db.scalar(
            select(WorkflowTransition).where(
                WorkflowTransition.from_state_id == current_state.id,
                WorkflowTransition.action_name == action_name,
            )
        )
        if not transition:
            raise ValueError(
                f"No transition '{action_name}' from '{current_state.name}'"
            )

        # Find target state
        target_state = await self.db.scalar(
            select(WorkflowState).where(WorkflowState.id == transition.to_state_id)
        )
        if not target_state:
            raise ValueError("Target state not found")

        # Update instance
        old_state = instance.current_state
        instance.current_state = target_state.name
        if target_state.is_final:
            instance.completed_at = datetime.now(timezone.utc)

        # Log action
        self.db.add(WorkflowAction(
            instance_id=instance.id,
            actor_id=actor_id,
            from_state=old_state,
            to_state=target_state.name,
            action=action_name,
            comment=comment,
        ))
        await self.db.flush()
        await self.db.refresh(instance)
        return instance

    async def get_instance(self, entity_type: str, entity_id: str) -> WorkflowInstance | None:
        """Find an active workflow instance for an entity."""
        return await self.db.scalar(
            select(WorkflowInstance)
            .join(WorkflowDefinition)
            .where(
                WorkflowDefinition.school_id == self.school_id,
                WorkflowDefinition.entity_type == entity_type,
                WorkflowInstance.entity_id == entity_id,
                WorkflowInstance.completed_at == None,
            )
        )

    async def get_history(self, instance_id: uuid.UUID) -> list[WorkflowAction]:
        rows = await self.db.scalars(
            select(WorkflowAction)
            .where(WorkflowAction.instance_id == instance_id)
            .order_by(WorkflowAction.created_at)
        )
        return list(rows)

    async def get_available_actions(
        self, instance_id: uuid.UUID, actor_role: str
    ) -> list[dict]:
        """What actions can this actor take right now?"""
        instance = await self.db.scalar(
            select(WorkflowInstance).where(WorkflowInstance.id == instance_id)
        )
        if not instance or instance.completed_at:
            return []

        wf = await self.db.scalar(
            select(WorkflowDefinition).where(WorkflowDefinition.id == instance.workflow_id)
        )

        current_state = await self.db.scalar(
            select(WorkflowState).where(
                WorkflowState.workflow_id == wf.id,
                WorkflowState.name == instance.current_state,
            )
        )
        if not current_state:
            return []

        # Admins can do anything
        can_act = (actor_role == current_state.required_role or
                   actor_role in ("school_admin", "platform_admin"))

        if not can_act:
            return []

        transitions = await self.db.scalars(
            select(WorkflowTransition).where(
                WorkflowTransition.from_state_id == current_state.id
            )
        )
        return [
            {"action": t.action_name, "display": t.display_name}
            for t in transitions
        ]
