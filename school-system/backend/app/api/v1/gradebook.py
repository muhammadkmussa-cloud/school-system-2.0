"""Gradebook routes — assessments & marks."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.core.dependencies import CurrentUser, DB, RequireStaff
from app.core.grading import compute_grade_letter
from app.models.assessment import Assessment, Mark
from app.models.student import Student
from app.schemas.gradebook import (
    AssessmentCreate,
    AssessmentOut,
    AssessmentStats,
    MarkEntry,
    MarkOut,
    StudentGrade,
)

router = APIRouter()


# ── Assessments ──────────────────────────────────────────────────────

@router.get("/assessments", response_model=list[AssessmentOut])
async def list_assessments(
    db: DB,
    current_user: RequireStaff,
    class_id: str = "",
    subject_id: str = "",
    term_id: str = "",
):
    base = select(Assessment).where(
        Assessment.school_id == current_user.school_id
    )
    if class_id:
        base = base.where(Assessment.class_id == uuid.UUID(class_id))
    if subject_id:
        base = base.where(Assessment.subject_id == uuid.UUID(subject_id))
    if term_id:
        base = base.where(Assessment.term_id == uuid.UUID(term_id))
    rows = await db.scalars(base.order_by(Assessment.created_at.desc()))
    return [AssessmentOut.model_validate(r) for r in rows]


@router.post("/assessments", response_model=AssessmentOut, status_code=201)
async def create_assessment(
    payload: AssessmentCreate, db: DB, current_user: RequireStaff
):
    # Resolve teacher profile from user
    from app.models.teacher import Teacher
    teacher = await db.scalar(
        select(Teacher).where(Teacher.user_id == current_user.id)
    )
    if not teacher:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No teacher profile linked to this account",
        )
    assessment = Assessment(
        school_id=current_user.school_id,
        teacher_id=teacher.id,
        **payload.model_dump(),
    )
    db.add(assessment)
    await db.flush()
    await db.refresh(assessment)
    return AssessmentOut.model_validate(assessment)


@router.get("/assessments/{assessment_id}", response_model=AssessmentOut)
async def get_assessment(
    assessment_id: uuid.UUID, db: DB, current_user: RequireStaff
):
    assessment = await db.scalar(
        select(Assessment).where(
            Assessment.id == assessment_id,
            Assessment.school_id == current_user.school_id,
        )
    )
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return AssessmentOut.model_validate(assessment)


# ── Marks ────────────────────────────────────────────────────────────

@router.post("/assessments/{assessment_id}/marks", status_code=201)
async def record_marks(
    assessment_id: uuid.UUID,
    payload: list[MarkEntry],
    db: DB,
    current_user: RequireStaff,
):
    """Record marks for an assessment in batch."""
    assessment = await db.scalar(
        select(Assessment).where(
            Assessment.id == assessment_id,
            Assessment.school_id == current_user.school_id,
        )
    )
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    for entry in payload:
        # Upsert
        existing = await db.scalar(
            select(Mark).where(
                Mark.assessment_id == assessment_id,
                Mark.student_id == entry.student_id,
                Mark.school_id == current_user.school_id,
            )
        )
        if existing:
            existing.score = entry.score
            existing.grade = compute_grade_letter(
                (entry.score / assessment.max_score) * 100
            )
            existing.remarks = entry.remarks
        else:
            db.add(
                Mark(
                    school_id=current_user.school_id,
                    assessment_id=assessment_id,
                    student_id=entry.student_id,
                    score=entry.score,
                    grade=compute_grade_letter(
                        (entry.score / assessment.max_score) * 100
                    ),
                    remarks=entry.remarks,
                )
            )
    await db.flush()
    return {"recorded": len(payload)}


@router.get("/assessments/{assessment_id}/marks", response_model=list[MarkOut])
async def get_marks(
    assessment_id: uuid.UUID, db: DB, current_user: RequireStaff
):
    marks = await db.scalars(
        select(Mark).where(
            Mark.assessment_id == assessment_id,
            Mark.school_id == current_user.school_id,
        )
    )
    return [MarkOut.model_validate(m) for m in marks]


@router.get("/assessments/{assessment_id}/stats", response_model=AssessmentStats)
async def assessment_stats(
    assessment_id: uuid.UUID, db: DB, current_user: RequireStaff
):
    """Compute stats for an assessment."""
    marks = await db.scalars(
        select(Mark).where(
            Mark.assessment_id == assessment_id,
            Mark.school_id == current_user.school_id,
        )
    )
    mark_list = marks.all()
    if not mark_list:
        return AssessmentStats(
            assessment_id=assessment_id,
            total_students=0,
            average=0,
            highest=0,
            lowest=0,
            class_average=0,
            grade_distribution={},
        )

    scores = [m.score for m in mark_list]
    avg = sum(scores) / len(scores)
    highest = max(scores)
    lowest = min(scores)

    dist: dict[str, int] = {}
    for m in mark_list:
        g = m.grade or "N/A"
        dist[g] = dist.get(g, 0) + 1

    return AssessmentStats(
        assessment_id=assessment_id,
        total_students=len(mark_list),
        average=round(avg, 2),
        highest=highest,
        lowest=lowest,
        class_average=round(avg, 2),
        grade_distribution=dist,
    )


@router.get("/student/{student_id}/grades", response_model=list[StudentGrade])
async def student_grades(
    student_id: uuid.UUID,
    db: DB,
    current_user: RequireStaff,
    term_id: str = "",
):
    """Get cumulative grades for a student."""
    from sqlalchemy.orm import selectinload

    base = (
        select(Mark)
        .join(Assessment)
        .where(
            Mark.student_id == student_id,
            Assessment.school_id == current_user.school_id,
        )
        .options(selectinload(Mark.assessment))
    )
    if term_id:
        base = base.where(Assessment.term_id == uuid.UUID(term_id))

    marks = await db.scalars(base)
    mark_list = marks.all()

    student = await db.scalar(select(Student).where(Student.id == student_id))

    weighted_sum = sum(
        m.score * (m.assessment.weight if m.assessment else 1)
        for m in mark_list
    )
    max_possible = sum(
        m.assessment.max_score * m.assessment.weight
        for m in mark_list
        if m.assessment
    ) or 1
    pct = (weighted_sum / max_possible) * 100

    return [
        StudentGrade(
            student_id=student_id,
            student_name=student.full_name if student else "",
            total=round(weighted_sum, 2),
            percentage=round(pct, 2),
            grade=compute_grade_letter(pct),
        )
    ]
