"""Academic structure routes — years, terms, classes, streams, subjects, departments."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.core.dependencies import DB, RequireSchoolAdmin, RequireStaff, Pagination
from app.models.academic import (
    AcademicYear,
    Class_,
    Department,
    Stream,
    Subject,
    Term,
)
from app.schemas.academic import (
    AcademicYearCreate,
    AcademicYearOut,
    ClassCreate,
    ClassOut,
    DepartmentCreate,
    DepartmentOut,
    StreamCreate,
    StreamOut,
    SubjectCreate,
    SubjectOut,
    TermCreate,
    TermOut,
)

router = APIRouter()


# ── Academic Years ───────────────────────────────────────────────────

@router.get("/years", response_model=list[AcademicYearOut])
async def list_years(db: DB, current_user: RequireStaff):
    rows = await db.scalars(
        select(AcademicYear)
        .where(AcademicYear.school_id == current_user.school_id)
        .order_by(AcademicYear.start_date.desc())
    )
    return [AcademicYearOut.model_validate(r) for r in rows]


@router.post("/years", response_model=AcademicYearOut, status_code=201)
async def create_year(
    payload: AcademicYearCreate, db: DB, current_user: RequireSchoolAdmin
):
    year = AcademicYear(school_id=current_user.school_id, **payload.model_dump())
    db.add(year)
    await db.flush()
    await db.refresh(year)
    return AcademicYearOut.model_validate(year)


@router.patch("/years/{year_id}", response_model=AcademicYearOut)
async def update_year(
    year_id: uuid.UUID,
    payload: AcademicYearCreate,
    db: DB,
    current_user: RequireSchoolAdmin,
):
    year = await db.scalar(
        select(AcademicYear).where(
            AcademicYear.id == year_id,
            AcademicYear.school_id == current_user.school_id,
        )
    )
    if not year:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(year, field, value)
    await db.flush()
    await db.refresh(year)
    return AcademicYearOut.model_validate(year)


# ── Terms ────────────────────────────────────────────────────────────

@router.get("/terms", response_model=list[TermOut])
async def list_terms(
    db: DB, current_user: RequireStaff, academic_year_id: str = ""
):
    base = select(Term).join(AcademicYear).where(
        AcademicYear.school_id == current_user.school_id
    )
    if academic_year_id:
        base = base.where(Term.academic_year_id == uuid.UUID(academic_year_id))
    rows = await db.scalars(base.order_by(Term.start_date))
    return [TermOut.model_validate(r) for r in rows]


@router.post("/terms", response_model=TermOut, status_code=201)
async def create_term(
    payload: TermCreate, db: DB, current_user: RequireSchoolAdmin
):
    # Verify academic year belongs to this school
    year = await db.scalar(
        select(AcademicYear).where(
            AcademicYear.id == payload.academic_year_id,
            AcademicYear.school_id == current_user.school_id,
        )
    )
    if not year:
        raise HTTPException(status_code=404, detail="Academic year not found")
    term = Term(**payload.model_dump(), school_id=current_user.school_id)
    db.add(term)
    await db.flush()
    await db.refresh(term)
    return TermOut.model_validate(term)


# ── Classes ──────────────────────────────────────────────────────────

@router.get("/classes", response_model=list[ClassOut])
async def list_classes(db: DB, current_user: RequireStaff):
    rows = await db.scalars(
        select(Class_)
        .where(Class_.school_id == current_user.school_id)
        .order_by(Class_.level, Class_.name)
    )
    return [ClassOut.model_validate(r) for r in rows]


@router.post("/classes", response_model=ClassOut, status_code=201)
async def create_class(
    payload: ClassCreate, db: DB, current_user: RequireSchoolAdmin
):
    klass = Class_(school_id=current_user.school_id, **payload.model_dump())
    db.add(klass)
    await db.flush()
    await db.refresh(klass)
    return ClassOut.model_validate(klass)


# ── Streams ──────────────────────────────────────────────────────────

@router.get("/streams", response_model=list[StreamOut])
async def list_streams(
    db: DB, current_user: RequireStaff, class_id: str = ""
):
    base = select(Stream).where(Stream.school_id == current_user.school_id)
    if class_id:
        base = base.where(Stream.class_id == uuid.UUID(class_id))
    rows = await db.scalars(base.order_by(Stream.name))
    return [StreamOut.model_validate(r) for r in rows]


@router.post("/streams", response_model=StreamOut, status_code=201)
async def create_stream(
    payload: StreamCreate, db: DB, current_user: RequireSchoolAdmin
):
    stream = Stream(school_id=current_user.school_id, **payload.model_dump())
    db.add(stream)
    await db.flush()
    await db.refresh(stream)
    return StreamOut.model_validate(stream)


# ── Subjects ─────────────────────────────────────────────────────────

@router.get("/subjects", response_model=list[SubjectOut])
async def list_subjects(db: DB, current_user: RequireStaff):
    rows = await db.scalars(
        select(Subject)
        .where(Subject.school_id == current_user.school_id)
        .order_by(Subject.name)
    )
    return [SubjectOut.model_validate(r) for r in rows]


@router.post("/subjects", response_model=SubjectOut, status_code=201)
async def create_subject(
    payload: SubjectCreate, db: DB, current_user: RequireSchoolAdmin
):
    subj = Subject(school_id=current_user.school_id, **payload.model_dump())
    db.add(subj)
    await db.flush()
    await db.refresh(subj)
    return SubjectOut.model_validate(subj)


# ── Departments ──────────────────────────────────────────────────────

@router.get("/departments", response_model=list[DepartmentOut])
async def list_departments(db: DB, current_user: RequireStaff):
    rows = await db.scalars(
        select(Department)
        .where(Department.school_id == current_user.school_id)
        .order_by(Department.name)
    )
    return [DepartmentOut.model_validate(r) for r in rows]


@router.post("/departments", response_model=DepartmentOut, status_code=201)
async def create_department(
    payload: DepartmentCreate, db: DB, current_user: RequireSchoolAdmin
):
    dept = Department(school_id=current_user.school_id, **payload.model_dump())
    db.add(dept)
    await db.flush()
    await db.refresh(dept)
    return DepartmentOut.model_validate(dept)
