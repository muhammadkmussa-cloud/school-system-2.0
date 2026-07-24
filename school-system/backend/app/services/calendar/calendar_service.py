"""School Management System — Calendar Integration Service.

Generates iCalendar (ICS) feeds from timetables and school events.
Supports Apple Calendar, Google Calendar, Outlook subscriptions.

Each teacher gets a personal calendar feed URL.
School admins get the master calendar.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.timetable import Timetable, TimetableEntry
from app.models.teacher import Teacher
from app.models.assessment import Assessment
from app.models.academic import Term, AcademicYear


class CalendarService:
    """Generates calendar data and ICS feeds."""

    def __init__(self, db: AsyncSession, school_id: uuid.UUID):
        self.db = db
        self.school_id = school_id

    async def get_teacher_timetable(
        self, teacher_user_id: uuid.UUID, week_start: date | None = None
    ) -> list[dict]:
        """Return a teacher's lessons for the current week as calendar events."""
        teacher = await self.db.scalar(
            select(Teacher).where(
                Teacher.user_id == teacher_user_id,
                Teacher.school_id == self.school_id,
            )
        )
        if not teacher:
            return []

        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())

        # Find active timetable
        timetable = await self.db.scalar(
            select(Timetable).where(
                Timetable.school_id == self.school_id,
                Timetable.is_active == True,
            )
        )
        if not timetable:
            return []

        entries = await self.db.scalars(
            select(TimetableEntry).where(
                TimetableEntry.timetable_id == timetable.id,
                TimetableEntry.teacher_id == teacher.id,
            )
        )

        events = []
        for entry in entries:
            event_date = week_start + timedelta(days=entry.day_of_week)
            start_dt = datetime.combine(event_date, entry.start_time)
            end_dt = datetime.combine(event_date, entry.end_time)

            events.append({
                "id": str(entry.id),
                "title": f"Lesson — Class {str(entry.class_id)[:8]}",
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "room": entry.room,
                "day_of_week": entry.day_of_week,
                "type": "lesson",
            })

        # Add assessments as calendar events
        assessments = await self.db.scalars(
            select(Assessment).where(
                Assessment.teacher_id == teacher.id,
                Assessment.school_id == self.school_id,
            )
        )
        for a in assessments:
            if a.date_administered:
                events.append({
                    "id": f"assess-{a.id}",
                    "title": f"Assessment: {a.name}",
                    "start": str(a.date_administered),
                    "type": "assessment",
                    "assessment_type": a.assessment_type,
                })

        return sorted(events, key=lambda e: e["start"])

    async def get_school_calendar(
        self, week_start: date | None = None
    ) -> list[dict]:
        """Return the full school calendar for a week."""
        if week_start is None:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())

        timetable = await self.db.scalar(
            select(Timetable).where(
                Timetable.school_id == self.school_id,
                Timetable.is_active == True,
            )
        )
        if not timetable:
            return []

        entries = await self.db.scalars(
            select(TimetableEntry).where(
                TimetableEntry.timetable_id == timetable.id,
            )
        )
        entry_list = list(entries)

        events: list[dict] = []
        for entry in entry_list:
            event_date = week_start + timedelta(days=entry.day_of_week)
            start_dt = datetime.combine(event_date, entry.start_time)
            end_dt = datetime.combine(event_date, entry.end_time)

            # Resolve teacher name
            teacher = await self.db.scalar(
                select(Teacher).where(Teacher.id == entry.teacher_id)
            )

            events.append({
                "id": str(entry.id),
                "title": f"Class {str(entry.class_id)[:8]} — Teacher: {teacher.full_name if teacher else 'N/A'}",
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "room": entry.room,
                "teacher_name": teacher.full_name if teacher else None,
                "day_of_week": entry.day_of_week,
                "type": "lesson",
            })

        # Add term dates
        terms = await self.db.scalars(
            select(Term).join(AcademicYear).where(
                AcademicYear.school_id == self.school_id,
            )
        )
        for t in terms:
            events.append({
                "id": f"term-{t.id}",
                "title": f"📅 {t.name}",
                "start": str(t.start_date),
                "end": str(t.end_date),
                "type": "term",
            })

        return sorted(events, key=lambda e: e["start"])

    def generate_ics_feed(self, events: list[dict], calendar_name: str = "School Management System Timetable") -> str:
        """Generate an iCalendar (ICS) feed string from events."""
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//School Management System//Timetable//EN",
            f"X-WR-CALNAME:{calendar_name}",
            "X-WR-TIMEZONE:Africa/Nairobi",
        ]

        for evt in events:
            # Format DTSTART/DTEND in iCal format
            dtstart = self._format_ical_dt(evt["start"])
            dtend = self._format_ical_dt(evt["end"])

            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{evt['id']}@example.com",
                f"DTSTART:{dtstart}",
                f"DTEND:{dtend}",
                f"SUMMARY:{evt['title']}",
                f"LOCATION:{evt.get('room', '')}",
                f"DESCRIPTION:{evt.get('type', 'lesson')} — School Management System",
                "END:VEVENT",
            ])

        lines.append("END:VCALENDAR")
        return "\r\n".join(lines)

    def _format_ical_dt(self, dt_str: str) -> str:
        """Convert ISO datetime string to iCal format (YYYYMMDDTHHMMSSZ)."""
        try:
            dt = datetime.fromisoformat(dt_str)
            return dt.strftime("%Y%m%dT%H%M%S")
        except ValueError:
            # Date only
            try:
                d = date.fromisoformat(dt_str)
                return d.strftime("%Y%m%d")
            except ValueError:
                return dt_str.replace("-", "").replace(":", "")[:15]

    async def get_upcoming_events(self, user_id: uuid.UUID, days: int = 7) -> list[dict]:
        """Get all upcoming events for a user in the next N days."""
        today = date.today()
        events = await self.get_teacher_timetable(user_id)

        upcoming = []
        for e in events:
            try:
                evt_date = date.fromisoformat(e["start"][:10])
                if today <= evt_date <= today + timedelta(days=days):
                    upcoming.append(e)
            except (ValueError, KeyError):
                continue

        return sorted(upcoming, key=lambda e: e["start"])
