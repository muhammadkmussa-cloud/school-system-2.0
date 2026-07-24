"""Exam workflow API — series, papers, scores, and exam-based results."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DB, RequireStaff, Pagination
from app.core.rbac import RequireExamsManage
from app.models.exam import ExamSeries, ExamPaper, ExamScore
from app.schemas.exam import ExamSeriesCreate, ExamPaperCreate, ExamScoreEntry
from app.services.exam.exam_engine import ExamEngine

router = APIRouter()


# ── Exam Series ──────────────────────────────────────────────────────

@router.get("/series", response_model=list[dict])
async def list_series(
    db: DB,
    current_user: RequireStaff,
    term_id: str = "",
):
    base = select(ExamSeries).where(ExamSeries.school_id == current_user.school_id)
    if term_id:
        base = base.where(ExamSeries.term_id == uuid.UUID(term_id))
    rows = await db.scalars(base.order_by(ExamSeries.start_date.desc()))
    return [
        {
            "id": str(r.id), "name": r.name, "series_type": r.series_type,
            "start_date": str(r.start_date), "end_date": str(r.end_date),
            "is_published": r.is_published, "weight_percentage": r.weight_percentage,
        }
        for r in rows
    ]


@router.post("/series", status_code=status.HTTP_201_CREATED)
async def create_series(
    payload: ExamSeriesCreate,
    db: DB,
    current_user: RequireExamsManage,
):
    series = ExamSeries(
        school_id=current_user.school_id,
        term_id=payload.term_id,
        name=payload.name,
        series_type=payload.series_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        weight_percentage=payload.weight_percentage,
    )
    db.add(series)
    await db.flush()
    await db.refresh(series)
    return {"id": str(series.id), "name": series.name}


# ── Exam Papers ──────────────────────────────────────────────────────

@router.post("/papers", status_code=status.HTTP_201_CREATED)
async def create_paper(payload: ExamPaperCreate, db: DB, current_user: RequireExamsManage):
    # Verify series belongs to this school
    series = await db.scalar(
        select(ExamSeries).where(
            ExamSeries.id == payload.series_id,
            ExamSeries.school_id == current_user.school_id,
        )
    )
    if not series:
        raise HTTPException(status_code=404, detail="Exam series not found")
    paper = ExamPaper(
        school_id=current_user.school_id,
        series_id=payload.series_id,
        subject_id=payload.subject_id,
        class_id=payload.class_id,
        name=payload.name,
        paper_code=payload.paper_code,
        max_score=payload.max_score,
        weight=payload.weight,
        duration_minutes=payload.duration_minutes,
        exam_date=payload.exam_date,
        instructions=payload.instructions,
    )
    db.add(paper)
    await db.flush()
    await db.refresh(paper)
    return {"id": str(paper.id), "name": paper.name}


@router.get("/papers/{series_id}", response_model=list[dict])
async def list_papers(series_id: uuid.UUID, db: DB, current_user: RequireStaff):
    rows = await db.scalars(
        select(ExamPaper).join(ExamSeries).where(
            ExamPaper.series_id == series_id,
            ExamSeries.school_id == current_user.school_id,
        )
    )
    return [
        {"id": str(r.id), "name": r.name, "paper_code": r.paper_code,
         "subject_id": str(r.subject_id), "class_id": str(r.class_id),
         "max_score": r.max_score, "weight": r.weight,
         "duration_minutes": r.duration_minutes, "exam_date": str(r.exam_date) if r.exam_date else None}
        for r in rows
    ]


# ── Scores ───────────────────────────────────────────────────────────

@router.post("/papers/{paper_id}/scores", status_code=201)
async def record_scores(
    paper_id: uuid.UUID,
    payload: list[ExamScoreEntry],
    db: DB,
    current_user: RequireStaff,
):
    # Verify paper belongs to this school
    paper = await db.scalar(
        select(ExamPaper).where(
            ExamPaper.id == paper_id,
            ExamPaper.school_id == current_user.school_id,
        )
    )
    if not paper:
        raise HTTPException(status_code=404, detail="Exam paper not found")
    for entry in payload:
        existing = await db.scalar(
            select(ExamScore).where(
                ExamScore.paper_id == paper_id,
                ExamScore.student_id == entry.student_id,
            )
        )
        if existing:
            existing.score = entry.score
            existing.is_absent = entry.is_absent
            existing.remarks = entry.remarks
        else:
            db.add(ExamScore(
                school_id=current_user.school_id,
                paper_id=paper_id,
                student_id=entry.student_id,
                score=entry.score,
                is_absent=entry.is_absent,
                remarks=entry.remarks,
            ))
    await db.flush()
    return {"recorded": len(payload)}


# ── Exam Results ─────────────────────────────────────────────────────

@router.get("/results/student/{student_id}")
async def student_exam_results(
    student_id: uuid.UUID,
    db: DB,
    current_user: RequireStaff,
    term_id: uuid.UUID = Query(...),
):
    engine = ExamEngine(db, current_user.school_id)
    report = await engine.compute_term_results(student_id, term_id)
    if not report:
        raise HTTPException(status_code=404, detail="No exam data found")
    return report


@router.get("/results/class/{class_id}/ranking")
async def class_exam_ranking(
    class_id: uuid.UUID,
    db: DB,
    current_user: RequireStaff,
    term_id: uuid.UUID = Query(...),
):
    engine = ExamEngine(db, current_user.school_id)
    rankings = await engine.class_exam_ranking(class_id, term_id)
    return {"rankings": rankings, "total": len(rankings)}
