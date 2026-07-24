"""School Management System — Bulk Import Engine.

Handles CSV and Excel imports for:
- Students (admission_number, full_name, gender, dob, class, stream, parent_*)
- Teachers (employee_number, full_name, email, phone)
- Marks / Scores (admission_number, subject_code, assessment_name, score)

Design: streaming parser that validates row-by-row and returns
detailed success/error reports.
"""

from __future__ import annotations

import csv
import io
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.student import Student
from app.models.teacher import Teacher
from app.models.user import User
from app.models.academic import Class_, Stream, Subject, AcademicYear
from app.models.assessment import Assessment, Mark
from app.core.security import hash_password


@dataclass
class ImportReport:
    total_rows: int = 0
    success: int = 0
    skipped: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)


class BulkImporter:
    """Streaming import with validation."""

    def __init__(self, db: AsyncSession, school_id: uuid.UUID):
        self.db = db
        self.school_id = school_id
        self._class_cache: dict[str, uuid.UUID] = {}
        self._stream_cache: dict[str, uuid.UUID] = {}
        self._subject_cache: dict[str, uuid.UUID] = {}
        self._year_cache: dict[str, uuid.UUID] = {}

    # ── Students ───────────────────────────────────────────────────

    STUDENT_COLUMNS = [
        "admission_number", "full_name", "gender", "date_of_birth",
        "class_name", "stream_name", "parent_name", "parent_phone",
        "parent_email", "medical_notes",
    ]

    async def import_students_csv(self, content: bytes) -> ImportReport:
        """Import students from CSV bytes."""
        report = ImportReport()

        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        rows = list(reader)
        report.total_rows = len(rows)

        # Pre-cache lookups
        await self._warm_caches()

        for i, row in enumerate(rows):
            try:
                # Validate required
                adm = (row.get("admission_number") or "").strip()
                name = (row.get("full_name") or "").strip()
                if not adm or not name:
                    report.errors.append({"row": i + 2, "error": "Missing admission_number or full_name"})
                    continue

                # Check duplicate
                existing = await self.db.scalar(
                    select(Student).where(
                        Student.school_id == self.school_id,
                        Student.admission_number == adm,
                    )
                )
                if existing:
                    report.skipped += 1
                    continue

                # Resolve class
                class_name = (row.get("class_name") or "").strip()
                class_id = await self._resolve_class(class_name)
                if not class_id:
                    report.errors.append({"row": i + 2, "error": f"Class '{class_name}' not found"})
                    continue

                # Resolve stream
                stream_name = (row.get("stream_name") or "").strip()
                stream_id = await self._resolve_stream(class_id, stream_name) if stream_name else None

                # Resolve academic year
                year_id = await self._resolve_current_year()

                # Parse date
                dob_str = (row.get("date_of_birth") or "").strip()
                dob = self._parse_date(dob_str) if dob_str else date(2008, 1, 1)

                gender = (row.get("gender") or "male").strip().lower()
                if gender not in ("male", "female", "other"):
                    gender = "male"

                student = Student(
                    school_id=self.school_id,
                    admission_number=adm,
                    full_name=name,
                    gender=gender,
                    date_of_birth=dob,
                    class_id=class_id,
                    stream_id=stream_id,
                    academic_year_id=year_id or uuid.uuid4(),  # fallback
                    parent_name=(row.get("parent_name") or "").strip() or None,
                    parent_phone=(row.get("parent_phone") or "").strip() or None,
                    parent_email=(row.get("parent_email") or "").strip() or None,
                    medical_notes=(row.get("medical_notes") or "").strip() or None,
                    status="active",
                )
                self.db.add(student)
                report.success += 1

            except Exception as e:
                report.errors.append({"row": i + 2, "error": str(e)})

        await self.db.flush()
        return report

    # ── Teachers ────────────────────────────────────────────────────

    async def import_teachers_csv(self, content: bytes) -> ImportReport:
        """Import teachers from CSV (creates User + Teacher)."""
        report = ImportReport()
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        rows = list(reader)
        report.total_rows = len(rows)

        for i, row in enumerate(rows):
            try:
                emp_no = (row.get("employee_number") or "").strip()
                name = (row.get("full_name") or "").strip()
                email = (row.get("email") or "").strip()

                if not emp_no or not name or not email:
                    report.errors.append({"row": i + 2, "error": "Missing required fields"})
                    continue

                # Check duplicate
                existing = await self.db.scalar(
                    select(Teacher).where(
                        Teacher.school_id == self.school_id,
                        Teacher.employee_number == emp_no,
                    )
                )
                if existing:
                    report.skipped += 1
                    continue

                # Create user account
                user = User(
                    school_id=self.school_id,
                    email=email,
                    hashed_password=hash_password("changeme123"),
                    full_name=name,
                    role="teacher",
                    is_active=True,
                    is_verified=True,
                )
                self.db.add(user)
                await self.db.flush()

                teacher = Teacher(
                    school_id=self.school_id,
                    user_id=user.id,
                    employee_number=emp_no,
                    full_name=name,
                    email=email,
                    phone=(row.get("phone") or "").strip() or None,
                )
                self.db.add(teacher)
                report.success += 1

            except Exception as e:
                report.errors.append({"row": i + 2, "error": str(e)})

        await self.db.flush()
        return report

    # ── Marks ───────────────────────────────────────────────────────

    async def import_marks_csv(
        self,
        content: bytes,
        assessment_id: uuid.UUID,
    ) -> ImportReport:
        """Import marks for a specific assessment.

        CSV columns: admission_number, score, [remarks]
        """
        report = ImportReport()
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        rows = list(reader)
        report.total_rows = len(rows)

        assessment = await self.db.scalar(
            select(Assessment).where(
                Assessment.id == assessment_id,
                Assessment.school_id == self.school_id,
            )
        )
        if not assessment:
            report.errors.append({"row": 0, "error": "Assessment not found"})
            return report

        for i, row in enumerate(rows):
            try:
                adm = (row.get("admission_number") or "").strip()
                score_str = (row.get("score") or "").strip()

                if not adm or not score_str:
                    report.errors.append({"row": i + 2, "error": "Missing admission_number or score"})
                    continue

                # Resolve student
                student = await self.db.scalar(
                    select(Student).where(
                        Student.school_id == self.school_id,
                        Student.admission_number == adm,
                    )
                )
                if not student:
                    report.errors.append({"row": i + 2, "error": f"Student '{adm}' not found"})
                    continue

                score = float(score_str)

                # Upsert
                existing = await self.db.scalar(
                    select(Mark).where(
                        Mark.assessment_id == assessment_id,
                        Mark.student_id == student.id,
                    )
                )
                if existing:
                    existing.score = score
                    existing.remarks = (row.get("remarks") or "").strip() or None
                else:
                    from app.core.grading import grade_for
                    pct = (score / assessment.max_score * 100) if assessment.max_score else 0
                    letter, _ = grade_for(pct)
                    self.db.add(Mark(
                        school_id=self.school_id,
                        assessment_id=assessment_id,
                        student_id=student.id,
                        score=score,
                        grade=letter,
                        remarks=(row.get("remarks") or "").strip() or None,
                    ))

                report.success += 1
            except ValueError:
                report.errors.append({"row": i + 2, "error": "Invalid score value"})
            except Exception as e:
                report.errors.append({"row": i + 2, "error": str(e)})

        await self.db.flush()
        return report

    # ── Helpers ─────────────────────────────────────────────────────

    async def _warm_caches(self):
        classes = await self.db.scalars(
            select(Class_).where(Class_.school_id == self.school_id)
        )
        self._class_cache = {c.name.lower(): c.id for c in classes}

        streams = await self.db.scalars(
            select(Stream).where(Stream.school_id == self.school_id)
        )
        self._stream_cache = {s.name.lower(): s.id for s in streams}

        subjects = await self.db.scalars(
            select(Subject).where(Subject.school_id == self.school_id)
        )
        self._subject_cache = {s.code.lower(): s.id for s in subjects}
        self._subject_cache.update({s.name.lower(): s.id for s in subjects})

    async def _resolve_class(self, name: str) -> uuid.UUID | None:
        key = name.lower()
        if key in self._class_cache:
            return self._class_cache[key]
        # Try lookup
        klass = await self.db.scalar(
            select(Class_).where(
                Class_.school_id == self.school_id,
                Class_.name.ilike(name),
            )
        )
        if klass:
            self._class_cache[key] = klass.id
            return klass.id
        return None

    async def _resolve_stream(self, class_id: uuid.UUID, name: str) -> uuid.UUID | None:
        key = name.lower()
        if key in self._stream_cache:
            return self._stream_cache[key]
        stream = await self.db.scalar(
            select(Stream).where(
                Stream.school_id == self.school_id,
                Stream.class_id == class_id,
                Stream.name.ilike(name),
            )
        )
        if stream:
            self._stream_cache[key] = stream.id
            return stream.id
        return None

    async def _resolve_current_year(self) -> uuid.UUID | None:
        year = await self.db.scalar(
            select(AcademicYear).where(
                AcademicYear.school_id == self.school_id,
                AcademicYear.is_current == True,
            )
        )
        return year.id if year else None

    def _parse_date(self, s: str) -> date:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
            try:
                return datetime.strptime(s.strip(), fmt).date()
            except ValueError:
                continue
        return date(2008, 1, 1)
