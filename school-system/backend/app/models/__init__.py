"""School Management System — ORM Models (v1.0)."""

from app.models.base import TimestampMixin
from app.models.school import School
from app.models.user import User, LoginHistory
from app.models.teacher import Teacher
from app.models.student import Student
from app.models.academic import AcademicYear, Term, Class_, Stream, Subject, Department
from app.models.timetable import Timetable, TimetableEntry
from app.models.attendance import AttendanceRecord
from app.models.assessment import Assessment, Mark
from app.models.lesson import LessonPlan
from app.models.assignment import Assignment, AssignmentSubmission
from app.models.billing import SchoolSubscription, Invoice, Payment
from app.models.curriculum import Curriculum, CurriculumLevel, GradingScheme, GradeBand, SchoolCurriculum
from app.models.exam import ExamSeries, ExamPaper, ExamScore
from app.models.workflow import WorkflowDefinition, WorkflowState, WorkflowTransition, WorkflowInstance, WorkflowAction
from app.models.audit import AuditLog
from app.models.notification import Notification

__all__ = [
    "TimestampMixin",
    "School",
    "User",
    "LoginHistory",
    "Teacher",
    "Student",
    "AcademicYear",
    "Term",
    "Class_",
    "Stream",
    "Subject",
    "Department",
    "Timetable",
    "TimetableEntry",
    "AttendanceRecord",
    "Assessment",
    "Mark",
    "LessonPlan",
    "Assignment",
    "AssignmentSubmission",
    "SchoolSubscription",
    "Invoice",
    "Payment",
    "Curriculum",
    "CurriculumLevel",
    "GradingScheme",
    "GradeBand",
    "SchoolCurriculum",
    "ExamSeries",
    "ExamPaper",
    "ExamScore",
    "WorkflowDefinition",
    "WorkflowState",
    "WorkflowTransition",
    "WorkflowInstance",
    "WorkflowAction",
    "AuditLog",
    "Notification",
]
