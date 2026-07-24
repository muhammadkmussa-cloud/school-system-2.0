"""School Management System — Staff Import Service.

Handles CSV and Excel validation and import for teacher accounts.
Provides row-by-row validation with detailed error reporting.
"""

from __future__ import annotations

import csv
import io
import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

EXPECTED_COLUMNS = [
    "full_name", "email", "phone", "employee_number",
    "role", "subjects", "assigned_classes", "assigned_streams",
]

REQUIRED_COLUMNS = ["full_name", "email"]


@dataclass
class StaffImportRow:
    row_number: int
    full_name: str
    email: str
    phone: str | None = None
    employee_number: str | None = None
    role: str = "teacher"
    subjects: list[str] = field(default_factory=list)
    assigned_classes: list[str] = field(default_factory=list)
    assigned_streams: list[str] = field(default_factory=list)


@dataclass
class StaffImportValidationError:
    row: int
    field: str
    message: str


@dataclass
class StaffImportResult:
    valid_rows: list[StaffImportRow] = field(default_factory=list)
    errors: list[StaffImportValidationError] = field(default_factory=list)
    total_rows: int = 0


class StaffImportService:
    """Validates and imports staff from CSV or Excel."""

    def __init__(self, db: AsyncSession, school_id: uuid.UUID):
        self.db = db
        self.school_id = school_id
        self._subject_cache: set[str] = set()
        self._class_cache: set[str] = set()
        self._stream_cache: set[str] = set()

    async def _warm_caches(self):
        from app.models.academic import Class_, Stream, Subject
        subjects = await self.db.scalars(
            select(Subject.name).where(Subject.school_id == self.school_id)
        )
        self._subject_cache = set(subjects.all())

        classes = await self.db.scalars(
            select(Class_.name).where(Class_.school_id == self.school_id)
        )
        self._class_cache = set(classes.all())

        streams = await self.db.scalars(
            select(Stream.name).where(Stream.school_id == self.school_id)
        )
        self._stream_cache = set(streams.all())

    async def validate_csv(self, content: bytes) -> StaffImportResult:
        """Validate a CSV file and return parsed rows + errors."""
        result = StaffImportResult()

        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except UnicodeDecodeError:
                result.errors.append(StaffImportValidationError(
                    row=0, field="file", message="Could not decode file. Use UTF-8 encoding."
                ))
                return result

        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        result.total_rows = len(rows)

        if not rows:
            return result

        # Check headers
        headers = set(reader.fieldnames or [])
        missing_headers = [c for c in REQUIRED_COLUMNS if c not in headers]
        if missing_headers:
            result.errors.append(StaffImportValidationError(
                row=0, field="headers",
                message=f"Missing required columns: {', '.join(missing_headers)}",
            ))
            return result

        await self._warm_caches()

        existing_emails: set[str] = set()
        for i, row in enumerate(rows):
            row_num = i + 2  # 1-indexed, +1 for header
            full_name = (row.get("full_name") or "").strip()
            email = (row.get("email") or "").strip().lower()
            phone = (row.get("phone") or "").strip() or None
            emp_num = (row.get("employee_number") or "").strip() or None
            role = (row.get("role") or "").strip().lower() or "teacher"

            # Validate required
            if not full_name:
                result.errors.append(StaffImportValidationError(
                    row=row_num, field="full_name", message="Full name is required"
                ))
                continue

            if not email:
                result.errors.append(StaffImportValidationError(
                    row=row_num, field="email", message="Email is required"
                ))
                continue

            if "@" not in email:
                result.errors.append(StaffImportValidationError(
                    row=row_num, field="email", message=f"Invalid email: {email}"
                ))
                continue

            # Duplicate email check
            if email in existing_emails:
                result.errors.append(StaffImportValidationError(
                    row=row_num, field="email",
                    message=f"Duplicate email in file: {email}",
                ))
                continue

            # Check DB for existing
            from app.models.user import User
            existing_user = await self.db.scalar(
                select(User).where(User.email == email)
            )
            if existing_user:
                result.errors.append(StaffImportValidationError(
                    row=row_num, field="email",
                    message=f"Email already exists in system: {email}",
                ))
                continue

            existing_emails.add(email)

            # Parse subjects, classes, streams (comma-separated)
            subjects_raw = (row.get("subjects") or "").strip()
            subjects = [s.strip() for s in subjects_raw.split(",") if s.strip()] if subjects_raw else []

            classes_raw = (row.get("assigned_classes") or "").strip()
            assigned_classes = [c.strip() for c in classes_raw.split(",") if c.strip()] if classes_raw else []

            streams_raw = (row.get("assigned_streams") or "").strip()
            assigned_streams = [s.strip() for s in streams_raw.split(",") if s.strip()] if streams_raw else []

            # Validate subjects
            invalid_subjects = [s for s in subjects if s not in self._subject_cache]
            if invalid_subjects and self._subject_cache:
                result.errors.append(StaffImportValidationError(
                    row=row_num, field="subjects",
                    message=f"Unknown subjects: {', '.join(invalid_subjects)}",
                ))
                continue

            # Validate classes
            invalid_classes = [c for c in assigned_classes if c not in self._class_cache]
            if invalid_classes and self._class_cache:
                result.errors.append(StaffImportValidationError(
                    row=row_num, field="assigned_classes",
                    message=f"Unknown classes: {', '.join(invalid_classes)}",
                ))
                continue

            # Validate streams
            invalid_streams = [s for s in assigned_streams if s not in self._stream_cache]
            if invalid_streams and self._stream_cache:
                result.errors.append(StaffImportValidationError(
                    row=row_num, field="assigned_streams",
                    message=f"Unknown streams: {', '.join(invalid_streams)}",
                ))
                continue

            result.valid_rows.append(StaffImportRow(
                row_number=row_num,
                full_name=full_name,
                email=email,
                phone=phone,
                employee_number=emp_num,
                role=role,
                subjects=subjects,
                assigned_classes=assigned_classes,
                assigned_streams=assigned_streams,
            ))

        return result

    async def validate_excel(self, content: bytes) -> StaffImportResult:
        """Validate an Excel (.xlsx) file using openpyxl."""
        result = StaffImportResult()

        try:
            import openpyxl
            wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
            ws = wb.active
            if ws is None:
                result.errors.append(StaffImportValidationError(
                    row=0, field="file", message="No worksheet found in the file"
                ))
                return result

            rows_iter = ws.iter_rows(values_only=True)
            header_row = next(rows_iter, None)
            if not header_row:
                result.errors.append(StaffImportValidationError(
                    row=0, field="file", message="File is empty"
                ))
                return result

            headers = [str(h).strip().lower().replace(" ", "_") if h else "" for h in header_row]
            missing_headers = [c for c in REQUIRED_COLUMNS if c not in headers]
            if missing_headers:
                result.errors.append(StaffImportValidationError(
                    row=0, field="headers",
                    message=f"Missing required columns: {', '.join(missing_headers)}",
                ))
                return result

            await self._warm_caches()

            rows_data = []
            for i, row_values in enumerate(rows_iter):
                row_dict = {}
                for j, val in enumerate(row_values):
                    if j < len(headers) and headers[j]:
                        row_dict[headers[j]] = str(val).strip() if val is not None else ""
                rows_data.append(row_dict)

            result.total_rows = len(rows_data)
            existing_emails: set[str] = set()

            for i, row in enumerate(rows_data):
                row_num = i + 2
                full_name = row.get("full_name", "").strip()
                email = row.get("email", "").strip().lower()

                if not full_name:
                    result.errors.append(StaffImportValidationError(row=row_num, field="full_name", message="Full name is required"))
                    continue
                if not email or "@" not in email:
                    result.errors.append(StaffImportValidationError(row=row_num, field="email", message=f"Invalid email: {email}"))
                    continue
                if email in existing_emails:
                    result.errors.append(StaffImportValidationError(row=row_num, field="email", message=f"Duplicate email: {email}"))
                    continue

                from app.models.user import User
                existing_user = await self.db.scalar(select(User).where(User.email == email))
                if existing_user:
                    result.errors.append(StaffImportValidationError(row=row_num, field="email", message=f"Email exists: {email}"))
                    continue

                existing_emails.add(email)
                phone = row.get("phone", "") or None
                emp_num = row.get("employee_number", "") or None

                subjects_raw = row.get("subjects", "")
                subjects = [s.strip() for s in subjects_raw.split(",") if s.strip()] if subjects_raw else []

                classes_raw = row.get("assigned_classes", "")
                assigned_classes = [c.strip() for c in classes_raw.split(",") if c.strip()] if classes_raw else []

                streams_raw = row.get("assigned_streams", "")
                assigned_streams = [s.strip() for s in streams_raw.split(",") if s.strip()] if streams_raw else []

                invalid_subjects = [s for s in subjects if s not in self._subject_cache]
                if invalid_subjects and self._subject_cache:
                    result.errors.append(StaffImportValidationError(row=row_num, field="subjects", message=f"Unknown: {', '.join(invalid_subjects)}"))
                    continue

                invalid_classes = [c for c in assigned_classes if c not in self._class_cache]
                if invalid_classes and self._class_cache:
                    result.errors.append(StaffImportValidationError(row=row_num, field="assigned_classes", message=f"Unknown: {', '.join(invalid_classes)}"))
                    continue

                invalid_streams = [s for s in assigned_streams if s not in self._stream_cache]
                if invalid_streams and self._stream_cache:
                    result.errors.append(StaffImportValidationError(row=row_num, field="assigned_streams", message=f"Unknown: {', '.join(invalid_streams)}"))
                    continue

                result.valid_rows.append(StaffImportRow(
                    row_number=row_num,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    employee_number=emp_num,
                    subjects=subjects,
                    assigned_classes=assigned_classes,
                    assigned_streams=assigned_streams,
                ))

            wb.close()
        except ImportError:
            result.errors.append(StaffImportValidationError(
                row=0, field="file", message="Excel support (openpyxl) is not installed"
            ))
        except Exception as e:
            result.errors.append(StaffImportValidationError(
                row=0, field="file", message=f"Error reading Excel file: {e}"
            ))

        return result

    @staticmethod
    def generate_csv_template() -> str:
        """Generate a CSV template for staff import."""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(EXPECTED_COLUMNS)
        writer.writerow([
            "Jane Wanjiku", "jane@school.ac.ke", "254712345678",
            "TCH001", "teacher", "Mathematics,English", "Form 1,Form 2", "East,West",
        ])
        writer.writerow([
            "John Kamau", "john@school.ac.ke", "254798765432",
            "TCH002", "teacher", "Kiswahili", "Form 1", "East",
        ])
        return output.getvalue()
