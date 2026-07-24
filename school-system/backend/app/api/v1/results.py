"""Results Engine & Report Cards API.

Exposes the grading engine — individual report cards, class rankings,
and PDF generation.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.core.dependencies import CurrentUser, DB, RequireStaff
from app.services.results_engine import ResultsEngine
from app.services.reports.pdf_report_card import generate_report_card_pdf

router = APIRouter()


async def _get_school_name(db, school_id: uuid.UUID) -> str:
    from app.models.school import School
    school = await db.scalar(select(School).where(School.id == school_id))
    return school.name if school else "School Management System for Schools"


@router.get("/student/{student_id}/report-card")
async def student_report_card(
    student_id: uuid.UUID,
    db: DB,
    current_user: RequireStaff,
    term_id: uuid.UUID = Query(...),
):
    """Generate a full report card in JSON format."""
    engine = ResultsEngine(db, current_user.school_id)
    report = await engine.compute_student_report(student_id, term_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student or data not found")
    return report


@router.get("/student/{student_id}/report-card/pdf")
async def student_report_card_pdf(
    student_id: uuid.UUID,
    db: DB,
    current_user: RequireStaff,
    term_id: uuid.UUID = Query(...),
):
    """Download a PDF report card."""
    engine = ResultsEngine(db, current_user.school_id)
    report = await engine.compute_student_report(student_id, term_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    pdf_bytes = generate_report_card_pdf(
        report,
        school_name=await _get_school_name(db, current_user.school_id),
    )

    filename = f"report_card_{report.admission_number}_{report.term_name.replace(' ', '_')}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/class/{class_id}/summary")
async def class_summary(
    class_id: uuid.UUID,
    db: DB,
    current_user: RequireStaff,
    term_id: uuid.UUID = Query(...),
):
    """Get aggregated class performance summary."""
    engine = ResultsEngine(db, current_user.school_id)
    return await engine.compute_class_summary(class_id, term_id)


@router.get("/class/{class_id}/rankings")
async def class_rankings(
    class_id: uuid.UUID,
    db: DB,
    current_user: RequireStaff,
    term_id: uuid.UUID = Query(...),
):
    """Full class ranking — every student sorted by mean."""
    from app.models.student import Student

    students = await db.scalars(
        select(Student).where(
            Student.class_id == class_id,
            Student.school_id == current_user.school_id,
            Student.status == "active",
        )
    )
    student_list = list(students)

    engine = ResultsEngine(db, current_user.school_id)
    rankings = []
    for s in student_list:
        mean = await engine.compute_mean_for_student(s.id, term_id)
        rankings.append({
            "student_id": str(s.id),
            "name": s.full_name,
            "admission_number": s.admission_number,
            "mean": round(mean, 2),
        })

    rankings.sort(key=lambda x: x["mean"], reverse=True)
    for i, r in enumerate(rankings):
        r["rank"] = i + 1

    return {"rankings": rankings, "total": len(rankings)}
