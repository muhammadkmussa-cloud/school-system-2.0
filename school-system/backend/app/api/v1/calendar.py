"""Calendar API — timetable events, ICS feeds."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from app.core.dependencies import CurrentUser, DB, RequireStaff
from app.services.calendar.calendar_service import CalendarService

router = APIRouter()


@router.get("/my")
async def my_calendar(
    db: DB,
    current_user: RequireStaff,
    week_start: str = "",
):
    """Get the current user's calendar for this week."""
    svc = CalendarService(db, current_user.school_id)
    ws = date.fromisoformat(week_start) if week_start else None
    events = await svc.get_teacher_timetable(current_user.id, ws)
    return {"events": events, "count": len(events)}


@router.get("/school")
async def school_calendar(
    db: DB,
    current_user: RequireStaff,
    week_start: str = "",
):
    """Get the full school calendar."""
    svc = CalendarService(db, current_user.school_id)
    ws = date.fromisoformat(week_start) if week_start else None
    events = await svc.get_school_calendar(ws)
    return {"events": events, "count": len(events)}


@router.get("/my.ics")
async def my_calendar_ics(db: DB, current_user: RequireStaff):
    """Download iCalendar feed for the current user."""
    svc = CalendarService(db, current_user.school_id)
    events = await svc.get_teacher_timetable(current_user.id)
    ics = svc.generate_ics_feed(events, f"School Management System — {current_user.full_name}")
    return PlainTextResponse(
        ics,
        media_type="text/calendar",
        headers={"Content-Disposition": "attachment; filename=school_system_timetable.ics"},
    )


@router.get("/upcoming")
async def upcoming_events(
    db: DB,
    current_user: RequireStaff,
    days: int = Query(7, le=30),
):
    """Get upcoming events for the next N days."""
    svc = CalendarService(db, current_user.school_id)
    events = await svc.get_upcoming_events(current_user.id, days)
    return {"events": events, "count": len(events)}
