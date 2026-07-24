"""School Management System — Subscription Lifecycle State Machine.

Implements the full customer journey:

    PENDING_VERIFICATION  (school registered, awaiting admin verification)
           ↓
    TRIAL                 (30-day full-feature trial, starts on verification)
           ↓
    ACTIVE                (paid subscription, recurring)
           ↓ (non-payment)
    EXPIRED               (read-only mode — all data preserved, no writes)
           ↓ (payment)
    ACTIVE                (reactivated)

    CANCELLED             (school explicitly cancels — data retained 90 days)

Read-only mode:
    - All GET endpoints work normally
    - Reports can be viewed and exported
    - No new attendance, marks, students, or other writes
    - Clear messaging: "Your trial has ended. Subscribe to continue."

This is designed to be friendly: schools never lose data, and they can
always see their reports even when expired.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any


class SubscriptionStatus(str, Enum):
    PENDING_VERIFICATION = "pending_verification"
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    EXPIRED = "expired"          # trial ended, read-only
    CANCELLED = "cancelled"      # explicit cancel
    SUSPENDED = "suspended"      # admin-blocked


# ── Read-only write methods (blocked when expired) ────────────────────

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Endpoints that should ALWAYS work even when expired:
ALWAYS_ALLOWED = {
    "POST /api/v1/auth/login",
    "POST /api/v1/auth/refresh",
    "POST /api/v1/auth/logout",
    "GET  /api/v1/auth/me",
    "GET  /api/v1/billing/tiers",
    "GET  /api/v1/billing/subscription",
    "POST /api/v1/billing/subscription/change",
    "POST /api/v1/billing/mpesa/pay",
    "POST /api/v1/billing/mpesa/callback",
    "POST /api/v1/billing/paystack/pay",
    "GET  /api/v1/billing/paystack/verify",
    "POST /api/v1/billing/paystack/webhook",
    "POST /api/v1/billing/mpesa/query",
    "GET  /api/v1/billing/subscription/check-feature",
    "GET  /health",
    "GET  /api/v1/health/full",
}

# Read-only is fine for these — GET + HEAD only
READ_ONLY_OK_PREFIXES = [
    "/api/v1/students", "/api/v1/teachers", "/api/v1/academic",
    "/api/v1/reports", "/api/v1/results", "/api/v1/analytics",
    "/api/v1/dashboard", "/api/v1/curriculum", "/api/v1/audit",
    "/api/v1/calendar", "/api/v1/lessons", "/api/v1/gradebook",
    "/api/v1/attendance", "/api/v1/timetable", "/api/v1/exams",
    "/api/v1/workflow", "/api/v1/assignments", "/api/v1/notifications",
    "/api/v1/sync", "/api/v1/promotion", "/api/v1/imports",
    "/api/v1/users", "/api/v1/schools",
]


@dataclass
class TrialConfig:
    duration_days: int = 30
    grace_period_days: int = 3   # extra days before read-only kicks in
    max_schools_per_phone: int = 1  # prevent trial abuse
    features: list[str] = field(default_factory=lambda: [
        "students_read", "students_create", "students_update",
        "teachers_read", "teachers_create",
        "classes_manage", "streams_manage", "subjects_manage",
        "academic_read", "academic_manage",
        "timetable_view", "timetable_manage",
        "attendance_write", "attendance_read",
        "marks_write", "marks_read",
        "lessons_write", "lessons_read",
        "reports_view", "reports_export",
        "results_view",
        "curriculum_read",
        "dashboard_admin", "dashboard_teacher",
    ])


def compute_subscription_state(
    sub: Any,  # SchoolSubscription
) -> dict[str, Any]:
    """Given a subscription row, compute the effective state with deadlines.

    Returns:
        {
            "status": "trial" | "active" | "expired" | ...,
            "effective_status": "active" | "read_only" | ...,
            "trial_days_left": int | None,
            "is_read_only": bool,
            "message": str (user-facing),
            "action_required": str | None,
        }
    """
    now = datetime.now(timezone.utc)
    status = sub.status if hasattr(sub, "status") else SubscriptionStatus.PENDING_VERIFICATION
    trial_ends = getattr(sub, "trial_ends_at", None)
    period_end = getattr(sub, "current_period_end", None)

    result: dict[str, Any] = {
        "status": status,
        "effective_status": "active",
        "is_read_only": False,
        "trial_days_left": None,
        "message": "",
        "action_required": None,
    }

    # ── Pending verification ──────────────────────────────────
    if status == SubscriptionStatus.PENDING_VERIFICATION.value:
        result["effective_status"] = "pending"
        result["message"] = "Your school is pending verification. An administrator will review your registration shortly."
        result["action_required"] = None
        return result

    # ── Trial ─────────────────────────────────────────────────
    if status == SubscriptionStatus.TRIAL.value and trial_ends:
        trial_end = trial_ends if isinstance(trial_ends, datetime) else datetime.fromisoformat(str(trial_ends))
        trial_end = trial_end.replace(tzinfo=timezone.utc) if trial_end.tzinfo is None else trial_end

        days_left = (trial_end - now).days

        if days_left <= -TrialConfig.grace_period_days:
            # Trial fully expired → read-only
            result["effective_status"] = "read_only"
            result["is_read_only"] = True
            result["trial_days_left"] = 0
            result["message"] = (
                "Your 30-day free trial has ended. All your data is safe and viewable. "
                "Subscribe now to continue recording attendance, marks, and generating reports."
            )
            result["action_required"] = "subscribe"
        elif days_left <= 0:
            # Grace period — still active, but warn
            result["effective_status"] = "active"
            result["trial_days_left"] = days_left
            result["message"] = (
                f"Your trial ended {-days_left} day(s) ago. You have "
                f"{TrialConfig.grace_period_days + days_left} grace day(s) remaining. "
                "Subscribe now to avoid interruption."
            )
            result["action_required"] = "subscribe_soon"
        else:
            result["effective_status"] = "active"
            result["trial_days_left"] = days_left
            result["message"] = (
                f"Trial: {days_left} day(s) remaining. "
                f"Full access to all features."
            )
        return result

    # ── Active (paid) ─────────────────────────────────────────
    if status == SubscriptionStatus.ACTIVE.value and period_end:
        pe = period_end if isinstance(period_end, datetime) else datetime.fromisoformat(str(period_end))
        pe = pe.replace(tzinfo=timezone.utc) if pe.tzinfo is None else pe

        if pe < now:
            # Past due — still active for 7 days grace
            days_past = (now - pe).days
            if days_past > 7:
                result["effective_status"] = "read_only"
                result["is_read_only"] = True
                result["message"] = (
                    "Your subscription has expired. Please renew to restore full access. "
                    "Your data is safe and viewable."
                )
                result["action_required"] = "renew"
            else:
                result["effective_status"] = "active"
                result["message"] = (
                    f"Your subscription is past due ({days_past} days). "
                    "Please update your payment method."
                )
                result["action_required"] = "update_payment"
        else:
            days_left = (pe - now).days
            result["effective_status"] = "active"
            result["message"] = f"Active subscription. {days_left} days remaining."
        return result

    # ── Expired / Cancelled / Suspended ───────────────────────
    if status in (
        SubscriptionStatus.EXPIRED.value,
        SubscriptionStatus.CANCELLED.value,
        SubscriptionStatus.SUSPENDED.value,
    ):
        result["effective_status"] = "read_only"
        result["is_read_only"] = True
        result["message"] = (
            "Your account is currently in read-only mode. "
            "All data is preserved. Contact support to reactivate."
        )
        result["action_required"] = "contact_support"
        return result

    # ── Past due ──────────────────────────────────────────────
    if status == SubscriptionStatus.PAST_DUE.value:
        result["effective_status"] = "active"
        result["message"] = "Your payment is past due. Please update your billing."
        result["action_required"] = "update_payment"
        return result

    return result


def is_write_method(method: str) -> bool:
    return method.upper() in WRITE_METHODS


def is_always_allowed(method: str, path: str) -> bool:
    """Check if this endpoint is exempt from read-only mode."""
    key = f"{method.upper():<5} {path}".strip()
    if key in ALWAYS_ALLOWED:
        return True
    # Check path prefixes for GET
    if method.upper() == "GET":
        for prefix in READ_ONLY_OK_PREFIXES:
            if path.startswith(prefix):
                return True
    return False
