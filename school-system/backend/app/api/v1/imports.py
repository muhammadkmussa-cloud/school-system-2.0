"""Bulk import API — CSV uploads for students, teachers, marks."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.core.dependencies import CurrentUser, DB
from app.core.rbac import RequireStudentImport
from app.services.imports.importer import BulkImporter

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post("/students/csv")
async def import_students_csv(
    file: UploadFile = File(...),
    db: DB = None,
    current_user: RequireStudentImport = None,
):
    """Upload a CSV of students. Returns success/error report."""
    if file.content_type and "csv" not in file.content_type and "text" not in file.content_type:
        raise HTTPException(status_code=400, detail="Please upload a CSV file")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    importer = BulkImporter(db, current_user.school_id)
    report = await importer.import_students_csv(content)
    return {
        "total_rows": report.total_rows,
        "success": report.success,
        "skipped": report.skipped,
        "errors": report.errors,
    }


@router.post("/teachers/csv")
async def import_teachers_csv(
    file: UploadFile = File(...),
    db: DB = None,
    current_user: RequireStudentImport = None,
):
    """Upload a CSV of teachers."""
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    importer = BulkImporter(db, current_user.school_id)
    report = await importer.import_teachers_csv(content)
    return {
        "total_rows": report.total_rows,
        "success": report.success,
        "skipped": report.skipped,
        "errors": report.errors,
    }


@router.post("/marks/csv")
async def import_marks_csv(
    assessment_id: uuid.UUID = Query(...),
    file: UploadFile = File(...),
    db: DB = None,
    current_user: RequireStudentImport = None,
):
    """Upload a CSV of marks for a specific assessment."""
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")

    importer = BulkImporter(db, current_user.school_id)
    report = await importer.import_marks_csv(content, assessment_id)
    return {
        "total_rows": report.total_rows,
        "success": report.success,
        "errors": report.errors,
    }


@router.get("/templates/students")
async def student_csv_template():
    """Return a sample CSV header for students."""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        "admission_number,full_name,gender,date_of_birth,class_name,stream_name,parent_name,parent_phone,parent_email,medical_notes\n"
        "MSS/2026/001,John Doe,male,2008-05-15,Form 1,East,Jane Doe,+254712345678,parent@email.com,\n",
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=student_import_template.csv"},
    )


@router.get("/templates/teachers")
async def teacher_csv_template():
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        "employee_number,full_name,email,phone\n"
        "TSC/001,Jane Teacher,jane@school.ac.ke,+254712345678\n",
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=teacher_import_template.csv"},
    )
