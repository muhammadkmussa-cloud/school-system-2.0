"""Student management routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.core.dependencies import CurrentUser, DB, RequireSchoolAdmin, RequireStaff, Pagination
from app.models.student import Student
from app.schemas.student import (
    StudentCreate,
    StudentList,
    StudentOut,
    StudentPromote,
    StudentTransfer,
    StudentUpdate,
)

router = APIRouter()


@router.get("", response_model=StudentList)
async def list_students(
    db: DB,
    current_user: RequireStaff,
    pagination: Pagination = Depends(),
    search: str = "",
    class_id: str = "",
    status: str = "active",
):
    """List students. Teachers see only their assigned students."""
    base = select(Student).where(Student.school_id == current_user.school_id)
    count_q = select(func.count(Student.id)).where(
        Student.school_id == current_user.school_id
    )

    if search:
        ilike = f"%{search}%"
        base = base.where(
            (Student.full_name.ilike(ilike))
            | (Student.admission_number.ilike(ilike))
        )
        count_q = count_q.where(
            (Student.full_name.ilike(ilike))
            | (Student.admission_number.ilike(ilike))
        )
    if class_id:
        base = base.where(Student.class_id == uuid.UUID(class_id))
        count_q = count_q.where(Student.class_id == uuid.UUID(class_id))
    if status:
        base = base.where(Student.status == status)
        count_q = count_q.where(Student.status == status)

    total = await db.scalar(count_q)
    rows = (
        await db.scalars(
            base.order_by(Student.full_name)
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
    ).all()

    return StudentList(
        items=[StudentOut.model_validate(r) for r in rows],
        total=total or 0,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
async def create_student(
    payload: StudentCreate, db: DB, current_user: RequireSchoolAdmin
):
    student = Student(
        school_id=current_user.school_id, **payload.model_dump()
    )
    db.add(student)
    await db.flush()
    await db.refresh(student)
    return StudentOut.model_validate(student)


@router.get("/{student_id}", response_model=StudentOut)
async def get_student(
    student_id: uuid.UUID, db: DB, current_user: RequireStaff
):
    student = await db.scalar(
        select(Student).where(
            Student.id == student_id,
            Student.school_id == current_user.school_id,
        )
    )
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return StudentOut.model_validate(student)


@router.patch("/{student_id}", response_model=StudentOut)
async def update_student(
    student_id: uuid.UUID,
    payload: StudentUpdate,
    db: DB,
    current_user: RequireSchoolAdmin,
):
    student = await db.scalar(
        select(Student).where(
            Student.id == student_id,
            Student.school_id == current_user.school_id,
        )
    )
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    await db.flush()
    await db.refresh(student)
    return StudentOut.model_validate(student)


@router.post("/{student_id}/transfer", response_model=StudentOut)
async def transfer_student(
    student_id: uuid.UUID,
    payload: StudentTransfer,
    db: DB,
    current_user: RequireSchoolAdmin,
):
    student = await db.scalar(
        select(Student).where(
            Student.id == student_id,
            Student.school_id == current_user.school_id,
        )
    )
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    student.class_id = payload.new_class_id
    student.stream_id = payload.new_stream_id
    student.status = "transferred"
    await db.flush()
    await db.refresh(student)
    return StudentOut.model_validate(student)


@router.post("/{student_id}/promote", response_model=StudentOut)
async def promote_student(
    student_id: uuid.UUID,
    payload: StudentPromote,
    db: DB,
    current_user: RequireSchoolAdmin,
):
    student = await db.scalar(
        select(Student).where(
            Student.id == student_id,
            Student.school_id == current_user.school_id,
        )
    )
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    student.class_id = payload.target_class_id
    student.academic_year_id = payload.target_academic_year_id
    student.stream_id = None
    await db.flush()
    await db.refresh(student)
    return StudentOut.model_validate(student)


@router.post("/{student_id}/archive", response_model=StudentOut)
async def archive_student(
    student_id: uuid.UUID, db: DB, current_user: RequireSchoolAdmin
):
    student = await db.scalar(
        select(Student).where(
            Student.id == student_id,
            Student.school_id == current_user.school_id,
        )
    )
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    student.status = "archived"
    await db.flush()
    await db.refresh(student)
    return StudentOut.model_validate(student)
