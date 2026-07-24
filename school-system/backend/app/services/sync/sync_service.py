"""School Management System — Offline-First Synchronization Engine.

Strategy:  Last-Write-Wins with conflict vectors for attendance & marks.
Devices cache data locally (Isar/Hive on Flutter, IndexedDB on web) and
sync when connectivity is restored.

Protocol:
    1. Client sends batch of local changes with timestamps
    2. Server merges, resolving conflicts with last-write-wins
    3. Server returns any server-side changes since client's last sync
    4. Client applies server changes to local store

Conflict resolution:
    - Attendance: last-write-wins on (student_id, date) key
    - Marks: last-write-wins on (assessment_id, student_id) key
    - Newer timestamp always wins
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from loguru import logger
from sqlalchemy import func, select

from app.core.config import settings

from app.models.attendance import AttendanceRecord
from app.models.assessment import Mark, Assessment
from app.models.student import Student


class SyncEntity(str, Enum):
    ATTENDANCE = "attendance"
    MARKS = "marks"


class SyncAction(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class SyncChange:
    entity: SyncEntity
    action: SyncAction
    payload: dict
    client_timestamp: str  # ISO 8601
    client_id: str  # device UUID
    change_id: str  # unique per change


@dataclass
class SyncResult:
    applied: int = 0
    conflicts: int = 0
    server_changes: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class SyncService:
    """Offline-first sync with conflict resolution."""

    def __init__(self, db, school_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.school_id = school_id
        self.user_id = user_id

    async def synchronize(
        self,
        changes: list[SyncChange],
        last_sync_at: str | None = None,
    ) -> SyncResult:
        """Process client changes and return server updates."""

        result = SyncResult()

        for change in changes:
            try:
                if change.entity == SyncEntity.ATTENDANCE:
                    await self._apply_attendance(change, result)
                elif change.entity == SyncEntity.MARKS:
                    await self._apply_marks(change, result)
            except Exception as e:
                result.errors.append(f"{change.change_id}: {str(e)}")

        await self.db.flush()

        # Return server-side changes since last sync
        if last_sync_at:
            result.server_changes = await self._get_server_changes(last_sync_at)

        return result

    async def _apply_attendance(self, change: SyncChange, result: SyncResult):
        """Merge attendance change using last-write-wins."""
        payload = change.payload
        student_id = uuid.UUID(payload["student_id"])
        attendance_date = payload["attendance_date"]

        client_ts = datetime.fromisoformat(change.client_timestamp.replace("Z", "+00:00"))

        existing = await self.db.scalar(
            select(AttendanceRecord).where(
                AttendanceRecord.student_id == student_id,
                AttendanceRecord.attendance_date == attendance_date,
            )
        )

        if existing:
            # Conflict: compare timestamps
            existing_ts = existing.updated_at
            if existing_ts and existing_ts > client_ts:
                # Server has newer data — skip
                result.conflicts += 1
                logger.debug(f"Conflict resolved (server wins): attendance {student_id} on {attendance_date}")
                return

            # Client wins or same timestamp
            existing.status = payload.get("status", existing.status)
            existing.remarks = payload.get("remarks", existing.remarks)
            existing.synced = True
            existing.recorded_by = self.user_id
            result.applied += 1
        else:
            self.db.add(AttendanceRecord(
                school_id=self.school_id,
                student_id=student_id,
                class_id=uuid.UUID(payload["class_id"]),
                recorded_by=self.user_id,
                attendance_date=attendance_date,
                status=payload.get("status", "present"),
                remarks=payload.get("remarks"),
                synced=True,
            ))
            result.applied += 1

    async def _apply_marks(self, change: SyncChange, result: SyncResult):
        """Merge marks change using last-write-wins."""
        payload = change.payload
        assessment_id = uuid.UUID(payload["assessment_id"])
        student_id = uuid.UUID(payload["student_id"])

        client_ts = datetime.fromisoformat(change.client_timestamp.replace("Z", "+00:00"))

        existing = await self.db.scalar(
            select(Mark).where(
                Mark.assessment_id == assessment_id,
                Mark.student_id == student_id,
            )
        )

        if existing:
            existing_ts = existing.updated_at
            if existing_ts and existing_ts > client_ts:
                result.conflicts += 1
                return

            existing.score = float(payload.get("score", existing.score))
            existing.remarks = payload.get("remarks", existing.remarks)
            existing.synced = True
            result.applied += 1
        else:
            self.db.add(Mark(
                school_id=self.school_id,
                assessment_id=assessment_id,
                student_id=student_id,
                score=float(payload.get("score", 0)),
                remarks=payload.get("remarks"),
                synced=True,
            ))
            result.applied += 1

    async def _get_server_changes(self, since_iso: str) -> list[dict]:
        """Fetch all attendance & mark changes made after *since_iso*."""
        since = datetime.fromisoformat(since_iso.replace("Z", "+00:00"))
        changes: list[dict] = []

        # Attendance changes (paginated — max 2000 per sync)
        att_records = await self.db.scalars(
            select(AttendanceRecord)
            .join(Student)
            .where(
                Student.school_id == self.school_id,
                AttendanceRecord.updated_at > since,
            )
            .limit(settings.OFFLINE_SYNC_BATCH_SIZE)
        )
        for r in att_records:
            changes.append({
                "entity": "attendance",
                "student_id": str(r.student_id),
                "class_id": str(r.class_id),
                "attendance_date": str(r.attendance_date),
                "status": r.status,
                "remarks": r.remarks,
                "server_updated_at": r.updated_at.isoformat() if r.updated_at else "",
            })

        # Marks changes (paginated — max BATCH_SIZE per sync)
        mark_records = await self.db.scalars(
            select(Mark)
            .join(Assessment)
            .where(
                Assessment.school_id == self.school_id,
                Mark.updated_at > since,
            )
            .limit(settings.OFFLINE_SYNC_BATCH_SIZE)
        )
        for m in mark_records:
            changes.append({
                "entity": "marks",
                "assessment_id": str(m.assessment_id),
                "student_id": str(m.student_id),
                "score": m.score,
                "grade": m.grade,
                "remarks": m.remarks,
                "server_updated_at": m.updated_at.isoformat() if m.updated_at else "",
            })

        return changes

    async def get_sync_status(self) -> dict:
        """Return counts of unsynced records for this school."""
        pending_attendance = await self.db.scalar(
            select(func.count(AttendanceRecord.id)).join(Student).where(
                Student.school_id == self.school_id,
                AttendanceRecord.synced == False,
            )
        )
        pending_marks = await self.db.scalar(
            select(func.count(Mark.id)).join(Assessment).where(
                Assessment.school_id == self.school_id,
                Mark.synced == False,
            )
        )
        return {
            "pending_attendance": pending_attendance or 0,
            "pending_marks": pending_marks or 0,
        }
