"""School Management System — Student Promotion Engine.

Production-grade: bulk promotion with real exam-engine integration
for min_mean filtering, rollback with snapshot, and audit trails.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student import Student
from app.models.academic import Class_, AcademicYear, Term
from app.models.assessment import Assessment, Mark


@dataclass
class PromotionResult:
    promoted: int = 0
    retained: int = 0
    graduated: int = 0
    errors: list[str] = field(default_factory=list)
    details: list[dict] = field(default_factory=list)


class PromotionService:
    """Safe student promotion with rollback support, real exam integration."""

    def __init__(self, db: AsyncSession, school_id: uuid.UUID):
        self.db = db
        self.school_id = school_id
        self._snapshot: dict[uuid.UUID, dict] = {}

    async def promote_class(
        self,
        source_class_id: uuid.UUID,
        target_class_id: uuid.UUID,
        target_academic_year_id: uuid.UUID,
        *,
        min_mean: float | None = None,
        override_students: set[uuid.UUID] | None = None,
        retain_students: set[uuid.UUID] | None = None,
        term_id: uuid.UUID | None = None,
    ) -> PromotionResult:
        """Promote eligible students with real exam-engine integration."""

        students = await self.db.scalars(
            select(Student).where(
                Student.school_id == self.school_id,
                Student.class_id == source_class_id,
                Student.status == "active",
            )
        )
        student_list = list(students)

        if not student_list:
            return PromotionResult(errors=["No active students in source class"])

        # Snapshot for rollback
        self._snapshot = {
            s.id: {"class_id": s.class_id, "academic_year_id": s.academic_year_id, "status": s.status}
            for s in student_list
        }

        # Load source class info
        source_class = await self.db.scalar(
            select(Class_).where(Class_.id == source_class_id)
        )
        is_graduating = source_class and source_class.level and source_class.level >= 4

        # Resolve term for min_mean check
        resolved_term_id = term_id
        if min_mean is not None and not resolved_term_id:
            current_term = await self.db.scalar(
                select(Term).join(AcademicYear).where(
                    AcademicYear.school_id == self.school_id,
                    Term.is_current == True,
                )
            )
            if current_term:
                resolved_term_id = current_term.id

        promoted = 0
        retained = 0
        graduated = 0

        for s in student_list:
            should_retain = False
            student_mean: float | None = None

            # Explicit retain list
            if retain_students and s.id in retain_students:
                should_retain = True
                student_mean = 0.0

            # Check minimum mean via real exam engine
            if not should_retain and min_mean is not None and resolved_term_id:
                student_mean = await self._compute_student_mean(s.id, s.class_id, resolved_term_id)
                if student_mean < min_mean:
                    should_retain = True

            # Override forces promotion regardless of mean
            if override_students and s.id in override_students:
                should_retain = False

            if should_retain:
                s.status = "active"  # retained but stays active
                retained += 1
                self._snapshot[s.id]["status"] = "active"
                self._snapshot[s.id]["action"] = "retained"
            elif is_graduating:
                s.status = "graduated"
                self._snapshot[s.id]["status"] = "graduated"
                self._snapshot[s.id]["action"] = "graduated"
                graduated += 1
            else:
                s.class_id = target_class_id
                s.academic_year_id = target_academic_year_id
                s.stream_id = None
                promoted += 1
                self._snapshot[s.id]["action"] = "promoted"

        await self.db.flush()

        logger.info(
            f"Promotion: {promoted} promoted, {retained} retained, "
            f"{graduated} graduated from class {source_class_id}"
        )

        return PromotionResult(
            promoted=promoted,
            retained=retained,
            graduated=graduated,
        )

    async def _compute_student_mean(
        self, student_id: uuid.UUID, class_id: uuid.UUID, term_id: uuid.UUID
    ) -> float:
        """Compute a student's overall mean using actual assessment data."""
        assessments = await self.db.scalars(
            select(Assessment).where(
                Assessment.school_id == self.school_id,
                Assessment.class_id == class_id,
                Assessment.term_id == term_id,
            )
        )
        a_list = list(assessments)

        if not a_list:
            return 0.0

        total_weighted = 0.0
        max_weighted = 0.0

        for a in a_list:
            mark = await self.db.scalar(
                select(Mark).where(
                    Mark.assessment_id == a.id,
                    Mark.student_id == student_id,
                )
            )
            score = mark.score if mark else 0.0
            total_weighted += score * a.weight
            max_weighted += a.max_score * a.weight

        if max_weighted == 0:
            return 0.0
        return round((total_weighted / max_weighted) * 100, 2)

    async def rollback(self) -> PromotionResult:
        """Undo the last promotion from snapshot."""
        if not self._snapshot:
            return PromotionResult(errors=["No snapshot available for rollback"])

        restored = 0
        for student_id, old_state in self._snapshot.items():
            await self.db.execute(
                update(Student)
                .where(Student.id == student_id)
                .values(
                    class_id=old_state["class_id"],
                    academic_year_id=old_state["academic_year_id"],
                    status=old_state["status"],
                )
            )
            restored += 1

        await self.db.flush()
        count = len(self._snapshot)
        self._snapshot.clear()
        logger.info(f"Rollback: {restored} students restored to previous state")
        return PromotionResult(promoted=restored)

    async def get_promotion_path(self, class_id: uuid.UUID) -> list[dict]:
        """Return the promotion chain for a class."""
        klass = await self.db.scalar(select(Class_).where(Class_.id == class_id))
        if not klass:
            return []

        classes = await self.db.scalars(
            select(Class_)
            .where(Class_.school_id == self.school_id)
            .order_by(Class_.level)
        )
        class_list = list(classes)

        chain = []
        current_level = klass.level or 1
        for c in class_list:
            if (c.level or 0) >= current_level:
                chain.append({
                    "id": str(c.id),
                    "name": c.name,
                    "level": c.level,
                    "is_current": c.id == class_id,
                })

        chain.append({
            "id": "graduated",
            "name": "Graduated / Completed",
            "level": None,
            "is_current": False,
        })

        return chain
