"""Lesson planning routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.core.dependencies import CurrentUser, DB, RequireStaff, Pagination
from app.models.lesson import LessonPlan
from app.schemas.lesson import LessonCreate, LessonDuplicate, LessonOut, LessonUpdate

router = APIRouter()


@router.get("", response_model=dict)
async def list_lessons(
    db: DB,
    current_user: RequireStaff,
    pagination: Pagination = Depends(),
    class_id: str = "",
    subject_id: str = "",
    status_filter: str = "",
):
    base = select(LessonPlan).where(LessonPlan.school_id == current_user.school_id)
    count_q = select(func.count(LessonPlan.id)).where(
        LessonPlan.school_id == current_user.school_id
    )

    if current_user.role == "teacher":
        # Find teacher profile
        from app.models.teacher import Teacher
        teacher = await db.scalar(
            select(Teacher).where(Teacher.user_id == current_user.id)
        )
        if teacher:
            base = base.where(LessonPlan.teacher_id == teacher.id)
            count_q = count_q.where(LessonPlan.teacher_id == teacher.id)

    if class_id:
        base = base.where(LessonPlan.class_id == uuid.UUID(class_id))
        count_q = count_q.where(LessonPlan.class_id == uuid.UUID(class_id))
    if subject_id:
        base = base.where(LessonPlan.subject_id == uuid.UUID(subject_id))
        count_q = count_q.where(LessonPlan.subject_id == uuid.UUID(subject_id))
    if status_filter:
        base = base.where(LessonPlan.completion_status == status_filter)
        count_q = count_q.where(LessonPlan.completion_status == status_filter)

    total = await db.scalar(count_q)
    rows = (
        await db.scalars(
            base.order_by(LessonPlan.created_at.desc())
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
    ).all()

    return {
        "items": [LessonOut.model_validate(r) for r in rows],
        "total": total or 0,
        "page": pagination.page,
        "page_size": pagination.page_size,
    }


@router.post("", response_model=LessonOut, status_code=status.HTTP_201_CREATED)
async def create_lesson(
    payload: LessonCreate, db: DB, current_user: RequireStaff
):
    from app.models.teacher import Teacher

    teacher = await db.scalar(
        select(Teacher).where(Teacher.user_id == current_user.id)
    )
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No teacher profile linked to this account",
        )

    lesson = LessonPlan(
        school_id=current_user.school_id,
        teacher_id=teacher.id,
        **payload.model_dump(),
    )
    db.add(lesson)
    await db.flush()
    await db.refresh(lesson)
    return LessonOut.model_validate(lesson)


@router.post("/duplicate", response_model=LessonOut, status_code=status.HTTP_201_CREATED)
async def duplicate_lesson(
    payload: LessonDuplicate, db: DB, current_user: RequireStaff
):
    """Clone an existing lesson plan."""
    source = await db.scalar(
        select(LessonPlan).where(
            LessonPlan.id == payload.source_plan_id,
            LessonPlan.school_id == current_user.school_id,
        )
    )
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    from app.models.teacher import Teacher

    teacher = await db.scalar(
        select(Teacher).where(Teacher.user_id == current_user.id)
    )

    new_plan = LessonPlan(
        school_id=current_user.school_id,
        teacher_id=teacher.id if teacher else source.teacher_id,
        subject_id=payload.subject_id or source.subject_id,
        class_id=payload.class_id or source.class_id,
        topic=source.topic,
        objectives=source.objectives,
        activities=source.activities,
        teaching_resources=source.teaching_resources,
        assessment=source.assessment,
        homework=source.homework,
        completion_status="planned",
        source_plan_id=source.id,
    )
    db.add(new_plan)
    await db.flush()
    await db.refresh(new_plan)
    return LessonOut.model_validate(new_plan)


@router.get("/{lesson_id}", response_model=LessonOut)
async def get_lesson(
    lesson_id: uuid.UUID, db: DB, current_user: RequireStaff
):
    lesson = await db.scalar(
        select(LessonPlan).where(
            LessonPlan.id == lesson_id,
            LessonPlan.school_id == current_user.school_id,
        )
    )
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return LessonOut.model_validate(lesson)


@router.patch("/{lesson_id}", response_model=LessonOut)
async def update_lesson(
    lesson_id: uuid.UUID,
    payload: LessonUpdate,
    db: DB,
    current_user: RequireStaff,
):
    lesson = await db.scalar(
        select(LessonPlan).where(
            LessonPlan.id == lesson_id,
            LessonPlan.school_id == current_user.school_id,
        )
    )
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lesson, field, value)
    await db.flush()
    await db.refresh(lesson)
    return LessonOut.model_validate(lesson)


@router.post("/{lesson_id}/complete", response_model=LessonOut)
async def mark_complete(
    lesson_id: uuid.UUID, db: DB, current_user: RequireStaff
):
    lesson = await db.scalar(
        select(LessonPlan).where(
            LessonPlan.id == lesson_id,
            LessonPlan.school_id == current_user.school_id,
        )
    )
    if not lesson:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    lesson.completion_status = "completed"
    await db.flush()
    await db.refresh(lesson)
    return LessonOut.model_validate(lesson)
