"""School Management System — Digital Assignment Service.

Assign → Notify → Collect → Grade workflow.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignment import Assignment, AssignmentSubmission
from app.models.student import Student
from app.models.teacher import Teacher


class AssignmentService:
    """Full assignment lifecycle management."""

    def __init__(self, db: AsyncSession, school_id: uuid.UUID, user_id: uuid.UUID):
        self.db = db
        self.school_id = school_id
        self.user_id = user_id

    async def create(self, data: dict) -> Assignment:
        """Teacher creates an assignment."""
        teacher = await self.db.scalar(
            select(Teacher).where(
                Teacher.user_id == self.user_id,
                Teacher.school_id == self.school_id,
            )
        )
        if not teacher:
            raise ValueError("No teacher profile linked")

        assignment = Assignment(
            school_id=self.school_id,
            teacher_id=teacher.id,
            subject_id=uuid.UUID(data["subject_id"]),
            class_id=uuid.UUID(data["class_id"]),
            title=data["title"],
            description=data.get("description"),
            assignment_type=data.get("assignment_type", "homework"),
            due_date=datetime.fromisoformat(data["due_date"]),
            max_score=data.get("max_score"),
            attachment_urls=data.get("attachment_urls"),
            allow_late_submission=data.get("allow_late_submission", True),
        )
        self.db.add(assignment)
        await self.db.flush()
        await self.db.refresh(assignment)
        return assignment

    async def list_for_teacher(
        self, page: int = 1, page_size: int = 20, class_id: str = ""
    ) -> tuple[list[Assignment], int]:
        """List assignments created by this teacher."""
        teacher = await self.db.scalar(
            select(Teacher).where(
                Teacher.user_id == self.user_id,
                Teacher.school_id == self.school_id,
            )
        )

        base = select(Assignment).where(Assignment.school_id == self.school_id)
        count_q = select(func.count(Assignment.id)).where(
            Assignment.school_id == self.school_id
        )

        if teacher:
            base = base.where(Assignment.teacher_id == teacher.id)
            count_q = count_q.where(Assignment.teacher_id == teacher.id)

        if class_id:
            base = base.where(Assignment.class_id == uuid.UUID(class_id))
            count_q = count_q.where(Assignment.class_id == uuid.UUID(class_id))

        total = await self.db.scalar(count_q)
        rows = (await self.db.scalars(
            base.order_by(Assignment.due_date.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )).all()

        return list(rows), total or 0

    async def get_submissions(
        self, assignment_id: uuid.UUID
    ) -> dict[str, Any]:
        """Get all submissions for an assignment with stats."""
        assignment = await self.db.scalar(
            select(Assignment).where(
                Assignment.id == assignment_id,
                Assignment.school_id == self.school_id,
            )
        )
        if not assignment:
            return {"error": "Not found"}

        submissions = await self.db.scalars(
            select(AssignmentSubmission).where(
                AssignmentSubmission.assignment_id == assignment_id,
            )
        )

        # Count expected students
        total_students = await self.db.scalar(
            select(func.count(Student.id)).where(
                Student.class_id == assignment.class_id,
                Student.school_id == self.school_id,
                Student.status == "active",
            )
        )

        sub_list = list(submissions)
        submitted = sum(1 for s in sub_list if s.submitted_at is not None)
        graded = sum(1 for s in sub_list if s.score is not None)
        late = sum(1 for s in sub_list if s.is_late)

        return {
            "assignment": {
                "id": str(assignment.id),
                "title": assignment.title,
                "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
                "max_score": assignment.max_score,
            },
            "stats": {
                "total_students": total_students or 0,
                "submitted": submitted,
                "pending": (total_students or 0) - submitted,
                "graded": graded,
                "late": late,
                "submission_rate": round((submitted / (total_students or 1)) * 100, 1),
            },
            "submissions": [
                {
                    "id": str(s.id),
                    "student_id": str(s.student_id),
                    "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
                    "is_late": s.is_late,
                    "score": s.score,
                    "grade": s.grade,
                    "teacher_comment": s.teacher_comment,
                }
                for s in sub_list
            ],
        }

    async def grade_submission(
        self, submission_id: uuid.UUID, score: float, comment: str = ""
    ) -> AssignmentSubmission:
        """Teacher grades a submission."""
        sub = await self.db.scalar(
            select(AssignmentSubmission).where(
                AssignmentSubmission.id == submission_id,
            )
        )
        if not sub:
            raise ValueError("Submission not found")

        sub.score = score
        sub.teacher_comment = comment or None
        sub.graded_at = datetime.now(timezone.utc)
        sub.graded_by = self.user_id

        # Compute grade from assignment's max_score
        assignment = await self.db.scalar(
            select(Assignment).where(Assignment.id == sub.assignment_id)
        )
        if assignment and assignment.max_score:
            from app.core.grading import grade_for
            pct = (score / assignment.max_score) * 100
            letter, _ = grade_for(pct)
            sub.grade = letter

        await self.db.flush()
        await self.db.refresh(sub)
        return sub
