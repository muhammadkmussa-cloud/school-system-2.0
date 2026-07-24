"""School Management System — Background Task Queue.

Uses Celery with Redis broker for:
- PDF report generation (batch)
- Notification dispatch (email, SMS, push)
- CSV import processing
- Ranking recalculations
- Scheduled jobs (attendance reminders, report publication)
"""
