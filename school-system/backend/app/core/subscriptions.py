"""School Management System — Subscription Tiers & Feature Flags.

Defines the monetization model with four tiers:
    free       — single teacher, personal productivity, no students DB
    starter    — small schools, up to 200 students, core modules
    professional — growing schools, analytics, workflows, imports, up to 1000 students
    enterprise — unlimited, multi-campus, API access, priority support

Feature flags are checked at the middleware level on every request.
Schools cannot access features above their tier.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ── Tier definitions ──────────────────────────────────────────────────


class Tier(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass
class TierConfig:
    name: str
    display: str
    price_monthly_kes: int  # Kenyan Shillings
    price_yearly_kes: int
    max_students: int
    max_teachers: int
    max_campuses: int
    features: list[str]
    highlights: list[str] = field(default_factory=list)
    color: str = "#6b7280"
    api_access: bool = False
    priority_support: bool = False
    custom_branding: bool = False
    dedicated_onboarding: bool = False


TIERS: dict[Tier, TierConfig] = {
    Tier.FREE: TierConfig(
        name="free",
        display="Free",
        price_monthly_kes=0,
        price_yearly_kes=0,
        max_students=0,         # no student DB
        max_teachers=1,
        max_campuses=1,
        highlights=["1 teacher account", "Personal timetable", "Lesson planner"],
        features=[
            "auth", "dashboard_teacher", "timetable_view",
            "lessons_write", "lessons_read",
            "timetable_view",
        ],
        color="#6b7280",
    ),
    Tier.STARTER: TierConfig(
        name="starter",
        display="Starter",
        price_monthly_kes=2_500,   # KES 2,500/month
        price_yearly_kes=25_000,   # KES 25,000/year (~2 months free)
        max_students=200,
        max_teachers=10,
        max_campuses=1,
        highlights=[
            "Up to 200 students", "10 teachers", "Attendance", "Marks & grading",
            "Report cards (PDF)", "Timetable management",
        ],
        features=[
            "auth", "dashboard_admin", "dashboard_teacher",
            "students_read", "students_create", "students_update",
            "teachers_read", "teachers_create",
            "classes_manage", "streams_manage", "subjects_manage",
            "academic_read", "academic_manage",
            "timetable_view", "timetable_manage",
            "attendance_write", "attendance_read",
            "marks_write", "marks_read",
            "lessons_write", "lessons_read",
            "reports_view", "reports_export",
            "results_view", "curriculum_read",
        ],
        color="#3b82f6",
    ),
    Tier.PROFESSIONAL: TierConfig(
        name="professional",
        display="Professional",
        price_monthly_kes=7_500,   # KES 7,500/month
        price_yearly_kes=75_000,   # KES 75,000/year
        max_students=1000,
        max_teachers=50,
        max_campuses=3,
        highlights=[
            "Up to 1,000 students", "50 teachers", "Advanced analytics",
            "Workflow approvals", "Bulk imports", "Audit trail",
            "Digital assignments", "Exam management",
        ],
        features=[
            # All starter features plus:
            "students_import", "students_promote", "students_transfer", "students_delete",
            "teachers_update", "teachers_manage",
            "timetable_manage",
            "reports_view", "reports_export", "reports_generate",
            "results_view", "results_export",
            "exams_read", "exams_manage",
            "analytics_view",
            "workflow_view", "workflow_approve",
            "imports_use",
            "assignments_read", "assignments_write",
            "curriculum_manage",
            "notifications_read", "notifications_send",
            "calendar_view",
        ],
        color="#8b5cf6",
    ),
    Tier.ENTERPRISE: TierConfig(
        name="enterprise",
        display="Enterprise",
        price_monthly_kes=25_000,  # KES 25,000/month
        price_yearly_kes=250_000,  # KES 250,000/year
        max_students=10_000,
        max_teachers=500,
        max_campuses=50,
        highlights=[
            "Unlimited students", "Unlimited teachers", "Multiple campuses",
            "API access", "Custom branding", "Priority support",
            "Dedicated onboarding", "SLA guarantee",
        ],
        features=[
            # Everything
            "auth", "dashboard_admin", "dashboard_teacher", "dashboard_advanced",
            "students_read", "students_create", "students_update", "students_delete",
            "students_import", "students_promote", "students_transfer",
            "teachers_read", "teachers_create", "teachers_update", "teachers_manage",
            "classes_manage", "streams_manage", "subjects_manage",
            "academic_read", "academic_manage",
            "timetable_view", "timetable_manage",
            "attendance_write", "attendance_read",
            "marks_write", "marks_read",
            "lessons_write", "lessons_read", "lessons_view_all",
            "reports_view", "reports_export", "reports_generate",
            "results_view", "results_export",
            "exams_read", "exams_manage",
            "analytics_view",
            "workflow_view", "workflow_approve",
            "audit_view",
            "imports_use",
            "promotion_manage",
            "assignments_read", "assignments_write",
            "curriculum_read", "curriculum_manage",
            "notifications_read", "notifications_send",
            "calendar_view", "calendar_manage",
            "sync_push", "sync_read",
            "settings_read", "settings_manage",
        ],
        api_access=True,
        priority_support=True,
        custom_branding=True,
        dedicated_onboarding=True,
        color="#059669",
    ),
}


def get_tier_config(tier: Tier | str) -> TierConfig:
    """Return the config for a tier."""
    if isinstance(tier, str):
        tier = Tier(tier)
    return TIERS.get(tier, TIERS[Tier.FREE])


def tier_has_feature(tier: Tier | str, feature: str) -> bool:
    """Check if a tier includes a specific feature."""
    config = get_tier_config(tier)
    return feature in config.features


def tier_allows_students(tier: Tier | str, count: int) -> bool:
    """Check if a tier allows the given number of students."""
    config = get_tier_config(tier)
    if config.max_students == 0:
        return False  # free tier: no student DB
    if config.max_students >= 10_000:
        return True  # enterprise: unlimited
    return count <= config.max_students


def tier_allows_teachers(tier: Tier | str, count: int) -> bool:
    """Check if a tier allows the given number of teachers."""
    config = get_tier_config(tier)
    if config.max_teachers >= 500:
        return True
    return count <= config.max_teachers


# ── Feature → permission mapping (for RBAC integration) ──────────────

TIER_FEATURE_TO_PERMISSION: dict[str, list[str]] = {
    "students_create":    ["students:create"],
    "students_read":      ["students:read"],
    "students_update":    ["students:update"],
    "students_delete":    ["students:delete"],
    "students_import":    ["students:import"],
    "students_promote":   ["students:promote"],
    "students_transfer":  ["students:transfer"],
    "teachers_create":    ["teachers:create"],
    "teachers_read":      ["teachers:read"],
    "teachers_update":    ["teachers:update"],
    "teachers_manage":    ["teachers:manage"],
    "classes_manage":     ["classes:manage"],
    "streams_manage":     ["streams:manage"],
    "subjects_manage":    ["subjects:manage"],
    "academic_read":      ["academic:read"],
    "academic_manage":    ["academic:manage"],
    "timetable_view":     ["timetable:view"],
    "timetable_manage":   ["timetable:manage"],
    "attendance_write":   ["attendance:write"],
    "attendance_read":    ["attendance:read"],
    "marks_write":        ["marks:write"],
    "marks_read":         ["marks:read"],
    "lessons_write":      ["lessons:write"],
    "lessons_read":       ["lessons:read"],
    "lessons_view_all":   ["lessons:view_all"],
    "reports_view":       ["reports:view"],
    "reports_export":     ["reports:export"],
    "reports_generate":   ["reports:generate"],
    "results_view":       ["reports:view"],
    "results_export":     ["reports:export"],
    "exams_read":         ["exams:read"],
    "exams_manage":       ["exams:manage"],
    "analytics_view":     ["analytics:view"],
    "workflow_view":      ["workflow:view"],
    "workflow_approve":   ["workflow:approve"],
    "audit_view":         ["audit:view"],
    "imports_use":        ["students:import"],
    "promotion_manage":   ["students:promote"],
    "assignments_read":   ["assignments:read"],
    "assignments_write":  ["assignments:write"],
    "curriculum_read":    ["settings:read"],
    "curriculum_manage":  ["settings:manage"],
    "notifications_read": ["notifications:read"],
    "notifications_send": ["notifications:send"],
    "calendar_view":      ["timetable:view"],
    "calendar_manage":    ["timetable:manage"],
    "sync_push":          ["sync:push"],
    "sync_read":          ["sync:read"],
    "settings_read":      ["settings:read"],
    "settings_manage":    ["settings:manage"],
}


def get_effective_permissions(tier: Tier | str) -> list[str]:
    """Return all RBAC permissions granted by a tier."""
    config = get_tier_config(tier)
    perms: list[str] = []
    for feature in config.features:
        perms.extend(TIER_FEATURE_TO_PERMISSION.get(feature, []))
    return list(set(perms))  # deduplicate
