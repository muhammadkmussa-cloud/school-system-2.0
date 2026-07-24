"""Onboarding API — school setup wizard & staff provisioning.

Three-step setup flow:
  1. School Information  — create school + academic year
  2. Academic Structure  — create classes, streams, subjects
  3. Staff Setup         — provision teacher accounts (manual or bulk import)
"""

from __future__ import annotations

import base64
from datetime import date, timedelta
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.core.dependencies import CurrentUser, DB, RequireSchoolAdmin
from app.models.academic import AcademicYear, Class_, Stream, Subject, Term
from app.models.school import School
from app.schemas.onboarding import (
    SchoolInfoStep,
    AcademicStructureStep,
    StaffSetupManual,
    StaffSetupBulk,
    StaffProvisioningResult,
    StaffValidationResult,
    TeacherCredentialOut,
    ValidationError,
)
from app.services.teacher_provisioning_service import TeacherProvisioningService
from app.services.staff_import_service import StaffImportService

router = APIRouter()


# ── Step 1: School Information ──────────────────────────────────────

@router.post("/setup/step-1", response_model=dict)
async def setup_step1_school(
    payload: SchoolInfoStep,
    db: DB,
    current_user: RequireSchoolAdmin,
):
    """Create the school profile and academic year."""
    # Check code uniqueness
    existing = await db.scalar(
        select(School).where(School.code == payload.code)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"School code '{payload.code}' is already taken",
        )

    # Update current user's school with the provided info
    school = await db.scalar(
        select(School).where(School.id == current_user.school_id)
    )
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    school.name = payload.name
    school.code = payload.code
    if payload.email:
        school.email = str(payload.email)
    if payload.phone:
        school.phone = payload.phone
    if payload.address:
        school.address = payload.address
    await db.flush()
    await db.refresh(school)

    # Create academic year
    year = AcademicYear(
        school_id=school.id,
        name=payload.academic_year_name,
        start_date=payload.academic_year_start,
        end_date=payload.academic_year_end,
        is_current=True,
    )
    db.add(year)
    await db.flush()

    return {
        "step": 1,
        "status": "completed",
        "school_id": str(school.id),
        "academic_year_id": str(year.id),
        "message": "School information saved and academic year created",
    }


# ── Step 2: Academic Structure ──────────────────────────────────────

@router.post("/setup/step-2", response_model=dict)
async def setup_step2_academic(
    payload: AcademicStructureStep,
    db: DB,
    current_user: RequireSchoolAdmin,
):
    """Create classes, streams, subjects, and terms."""
    school_id = current_user.school_id

    # Get the academic year (most recent one)
    year = await db.scalar(
        select(AcademicYear).where(
            AcademicYear.school_id == school_id,
            AcademicYear.is_current == True,
        ).order_by(AcademicYear.created_at.desc()).limit(1)
    )
    if not year:
        raise HTTPException(status_code=400, detail="No academic year found. Complete Step 1 first.")

    created_classes = []
    created_streams = []
    created_subjects = []

    # Create grades/classes and streams
    for grade in payload.grades:
        class_ = Class_(
            school_id=school_id,
            name=grade.name,
            level=grade.level,
        )
        db.add(class_)
        await db.flush()
        created_classes.append({"id": str(class_.id), "name": class_.name})

        for snum in range(1, grade.num_streams + 1):
            stream_name = f"Stream {['First', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth', 'Seventh', 'Eighth', 'Ninth', 'Tenth'][snum - 1] if snum <= 10 else str(snum)}"
            if grade.num_streams <= 2:
                stream_name = ["East", "West"][snum - 1]
            elif grade.num_streams == 3:
                stream_name = ["East", "West", "North"][snum - 1]

            stream = Stream(
                school_id=school_id,
                class_id=class_.id,
                name=stream_name,
            )
            db.add(stream)
            await db.flush()
            created_streams.append({"id": str(stream.id), "name": stream_name, "class_id": str(class_.id)})

    # Create subjects
    for subject in payload.subjects:
        subj = Subject(
            school_id=school_id,
            code=subject.code,
            name=subject.name,
        )
        db.add(subj)
        await db.flush()
        created_subjects.append({"id": str(subj.id), "code": subj.code, "name": subj.name})

    # Create terms (3 by default)
    if year and payload.term_names:
        term_count = len(payload.term_names)
        if term_count == 3:
            terms_data = [
                (1, year.start_date, date_with_offset(year.start_date, 90)),
                (2, date_with_offset(year.start_date, 120), date_with_offset(year.start_date, 210)),
                (3, date_with_offset(year.start_date, 240), year.end_date),
            ]
        else:
            terms_data = [
                (i + 1, date_with_offset(year.start_date, i * (365 // term_count)), date_with_offset(year.start_date, (i + 1) * (365 // term_count) - 7))
                for i in range(term_count)
            ]

        for tnum, tstart, tend in terms_data:
            term = Term(
                school_id=school_id,
                academic_year_id=year.id,
                name=payload.term_names[tnum - 1] if tnum - 1 < len(payload.term_names) else f"Term {tnum}",
                term_number=tnum,
                start_date=tstart,
                end_date=tend,
                is_current=(tnum == 1),
            )
            db.add(term)
        await db.flush()

    return {
        "step": 2,
        "status": "completed",
        "classes": created_classes,
        "streams": created_streams,
        "subjects": created_subjects,
        "message": f"{len(created_classes)} classes, {len(created_streams)} streams, and {len(created_subjects)} subjects created",
    }


def date_with_offset(d: date, days: int) -> date:
    """Add days to a date."""
    return d + timedelta(days=days)


# ── Step 3: Staff Setup — Manual Entry ─────────────────────────────

@router.post("/setup/step-3/manual", response_model=StaffProvisioningResult)
async def setup_step3_staff_manual(
    payload: StaffSetupManual,
    db: DB,
    current_user: RequireSchoolAdmin,
):
    """Provision teacher accounts from a manually entered staff list."""
    svc = TeacherProvisioningService(db, current_user.school_id)
    staff_dicts = [
        {
            "full_name": s.full_name,
            "email": str(s.email),
            "phone": s.phone,
            "employee_number": s.employee_number,
        }
        for s in payload.staff_list
    ]
    result = await svc.provision_from_list(staff_dicts)

    return StaffProvisioningResult(
        total_created=result.created,
        teachers=[
            TeacherCredentialOut(
                id=t.id,
                employee_number=t.employee_number,
                full_name=t.full_name,
                email=t.email,
                temp_password=t.temp_password,
                is_active=t.is_active,
            )
            for t in result.teachers
        ],
    )


# ── Step 3: Staff Setup — Validate Import File ─────────────────────

@router.post("/setup/step-3/validate", response_model=StaffValidationResult)
async def setup_step3_validate_import(
    db: DB,
    current_user: RequireSchoolAdmin,
    payload: StaffSetupBulk,
):
    """Validate a CSV or Excel file before importing."""
    try:
        content = base64.b64decode(payload.file_content)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 encoding")

    svc = StaffImportService(db, current_user.school_id)

    if payload.filename.lower().endswith(".csv"):
        result = await svc.validate_csv(content)
    elif payload.filename.lower().endswith(".xlsx"):
        result = await svc.validate_excel(content)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format. Use .csv or .xlsx")

    preview = [
        {
            "full_name": r.full_name,
            "email": r.email,
            "phone": r.phone,
            "employee_number": r.employee_number,
            "subjects": r.subjects,
            "assigned_classes": r.assigned_classes,
            "assigned_streams": r.assigned_streams,
        }
        for r in result.valid_rows[:10]
    ]

    return StaffValidationResult(
        valid=len(result.errors) == 0,
        total_rows=result.total_rows,
        valid_rows=len(result.valid_rows),
        errors=[
            ValidationError(row=e.row, field=e.field, message=e.message)
            for e in result.errors
        ],
        preview=preview,
    )


# ── Step 3: Staff Setup — Confirm Import ───────────────────────────

@router.post("/setup/step-3/confirm", response_model=StaffProvisioningResult)
async def setup_step3_confirm_import(
    db: DB,
    current_user: RequireSchoolAdmin,
    payload: StaffSetupBulk,
):
    """Import staff from a validated CSV/Excel file."""
    try:
        content = base64.b64decode(payload.file_content)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid base64 encoding")

    svc_validate = StaffImportService(db, current_user.school_id)

    if payload.filename.lower().endswith(".csv"):
        result = await svc_validate.validate_csv(content)
    elif payload.filename.lower().endswith(".xlsx"):
        result = await svc_validate.validate_excel(content)
    else:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    if result.errors:
        raise HTTPException(
            status_code=400,
            detail=f"File has {len(result.errors)} validation error(s). Validate first.",
        )

    if not result.valid_rows:
        raise HTTPException(status_code=400, detail="No valid rows to import")

    svc_provision = TeacherProvisioningService(db, current_user.school_id)
    staff_dicts = [
        {
            "full_name": r.full_name,
            "email": r.email,
            "phone": r.phone,
            "employee_number": r.employee_number,
            "subjects": r.subjects,
            "assigned_classes": r.assigned_classes,
            "assigned_streams": r.assigned_streams,
        }
        for r in result.valid_rows
    ]
    provision_result = await svc_provision.provision_from_list(staff_dicts)

    return StaffProvisioningResult(
        total_created=provision_result.created,
        teachers=[
            TeacherCredentialOut(
                id=t.id,
                employee_number=t.employee_number,
                full_name=t.full_name,
                email=t.email,
                temp_password=t.temp_password,
                is_active=t.is_active,
            )
            for t in provision_result.teachers
        ],
    )


# ── Import template download ────────────────────────────────────────

@router.get("/setup/staff-template")
async def download_staff_template():
    """Download a CSV template for staff import."""
    from app.services.staff_import_service import StaffImportService
    csv_content = StaffImportService.generate_csv_template()
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=staff_import_template.csv"},
    )


# ── Check setup status ─────────────────────────────────────────────

@router.get("/setup/status")
async def get_setup_status(
    db: DB,
    current_user: RequireSchoolAdmin,
):
    """Check what setup steps have been completed."""
    school_id = current_user.school_id
    school = await db.scalar(select(School).where(School.id == school_id))

    classes_count = await db.scalar(
        select(func.count(Class_.id)).where(Class_.school_id == school_id)
    )
    subjects_count = await db.scalar(
        select(func.count(Subject.id)).where(Subject.school_id == school_id)
    )
    teachers_count = await db.scalar(
        select(func.count(Term.id)).where(Term.school_id == school_id)
    )
    from app.models.teacher import Teacher
    teacher_count = await db.scalar(
        select(func.count(Teacher.id)).where(Teacher.school_id == school_id)
    )

    return {
        "school_configured": bool(school and school.name),
        "academic_structure_created": (classes_count or 0) > 0 and (subjects_count or 0) > 0,
        "staff_provisioned": (teacher_count or 0) > 0,
        "teacher_count": teacher_count or 0,
        "class_count": classes_count or 0,
        "subject_count": subjects_count or 0,
    }
