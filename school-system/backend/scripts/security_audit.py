#!/usr/bin/env python3
"""School Management System — Automated Security Audit.

Scans the entire codebase for:
1. Endpoints missing school-scoping (school_id filter)
2. Endpoints missing RBAC dependency injection
3. Hardcoded secrets or credentials
4. SQL injection risks (raw SQL without parameterization)
5. Unvalidated path/user input in queries

Run: python -m scripts.security_audit
"""

from __future__ import annotations

import ast
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# ── Project root ──────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
API_DIR = PROJECT_ROOT / "app" / "api"

# ── Findings collectors ──────────────────────────────────────────
findings: dict[str, list[str]] = defaultdict(list)
stats = {"files_scanned": 0, "endpoints_found": 0, "endpoints_secured": 0,
         "endpoints_scoped": 0, "issues_found": 0}


def add_finding(severity: str, path: str, message: str):
    findings[severity].append(f"{path}: {message}")
    stats["issues_found"] += 1


# ── Checkers ─────────────────────────────────────────────────────

SECRET_PATTERNS = [
    (r'SECRET_KEY\s*=\s*"[^"]{1,20}"', "Short/weak SECRET_KEY"),
    (r'password\s*=\s*"[^"]{1,8}"', "Short/hardcoded password"),
    (r'api_key\s*=\s*"[^"]+"', "Hardcoded API key"),
    (r'token\s*=\s*"eyJ[A-Za-z0-9_-]{10,}"', "Hardcoded JWT token"),
]

ROLES_WITH_ACCESS = {
    "RequireStaff", "RequireSchoolAdmin", "RequirePlatformAdmin",
    "RequireTeacher", "RequireStudentCreate", "RequireStudentRead",
    "RequireStudentPromote", "RequireStudentImport",
    "RequireAttendanceWrite", "RequireMarksWrite",
    "RequireReportsExport", "RequireExamsManage",
    "RequireTimetableManage", "RequireSettingsManage",
    "RequireClassesManage", "CurrentUser",
}

SCHOOL_SCOPED_MODELS = [
    "Student", "Teacher", "Assessment", "Mark", "AttendanceRecord",
    "LessonPlan", "Timetable", "TimetableEntry", "Class_", "Stream",
    "Subject", "Department", "AcademicYear", "Term", "ExamSeries",
    "ExamPaper", "Assignment",
]


def scan_file(filepath: Path):
    """Scan a single Python file for security issues."""
    try:
        source = filepath.read_text(encoding="utf-8")
    except Exception:
        return

    stats["files_scanned"] += 1
    relpath = str(filepath.relative_to(PROJECT_ROOT))

    # ── 1. Hardcoded secrets ──────────────────────────────────
    for pattern, desc in SECRET_PATTERNS:
        if re.search(pattern, source):
            add_finding("HIGH", relpath, f"Potential {desc}")

    # ── 2. Endpoint analysis ──────────────────────────────────
    if "api/v1" in relpath or "api/public" in relpath:
        # Count route decorators
        routes = re.findall(r'@router\.(get|post|patch|put|delete)\(', source)
        stats["endpoints_found"] += len(routes)

        # Check RBAC usage
        for role_dep in ROLES_WITH_ACCESS:
            if role_dep in source:
                stats["endpoints_secured"] += 1
                break

        # Check school scoping
        if "school_id" in source or "current_user.school_id" in source:
            stats["endpoints_scoped"] += 1
        elif routes:  # has routes but no school_id mention
            add_finding(
                "MEDIUM", relpath,
                f"Endpoint may lack school-scoping ({len(routes)} routes found)"
            )

    # ── 3. Raw SQL injection risks ────────────────────────────
    raw_sql = re.findall(r'\.execute\(text\(["\'](.+?)["\']\)', source)
    for sql in raw_sql:
        if ":" not in sql and "%(" not in sql:  # not parameterized
            add_finding("HIGH", relpath, f"Unparameterized SQL: {sql[:80]}")

    # ── 4. f-string in SQL ──────────────────────────────────
    if re.search(r'text\(f["\']', source):
        add_finding("HIGH", relpath, "f-string in SQL — injection risk")

    # ── 5. No where clause on select ─────────────────────────
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = ""
            if isinstance(node.func, ast.Attribute):
                func_name = node.func.attr
            elif isinstance(node.func, ast.Name):
                func_name = node.func.id

            if func_name == "select" and not _has_where_clause(node):
                # Check if this is a model with school_id
                for arg in node.args:
                    if isinstance(arg, ast.Name) and arg.id in SCHOOL_SCOPED_MODELS:
                        add_finding(
                            "MEDIUM", relpath,
                            f"select({arg.id}) without WHERE clause — may miss school-scoping"
                        )


def _has_where_clause(call_node: ast.Call) -> bool:
    """Check if a select() call has a .where() chained."""
    # Walk parent tree for .where attribute
    for parent in ast.walk(call_node):
        if isinstance(parent, ast.Attribute) and parent.attr == "where":
            return True
    # Also check for .where directly on call
    if isinstance(call_node.parent, ast.Attribute):
        return call_node.parent.attr == "where"
    return False


def scan_all():
    """Scan entire project."""
    print(f"\n{'='*60}")
    print("  School Management System — Security Audit")
    print(f"{'='*60}\n")

    for filepath in PROJECT_ROOT.rglob("*.py"):
        if "__pycache__" in str(filepath) or "node_modules" in str(filepath):
            continue
        if "alembic/versions" in str(filepath):
            continue
        scan_file(filepath)

    # ── Print report ──────────────────────────────────────────
    print(f"  Files scanned:      {stats['files_scanned']}")
    print(f"  Endpoints found:    {stats['endpoints_found']}")
    print(f"  Endpoints secured:  {stats['endpoints_secured']} (RBAC dependency detected)")
    print(f"  Endpoints scoped:   {stats['endpoints_scoped']} (school_id filter detected)")
    print(f"  Issues found:       {stats['issues_found']}")
    print()

    for severity in ("HIGH", "MEDIUM", "LOW"):
        if findings[severity]:
            print(f"  ── {severity} Severity ({len(findings[severity])}) ──")
            for f in findings[severity][:15]:
                print(f"    • {f}")
            if len(findings[severity]) > 15:
                print(f"    … and {len(findings[severity]) - 15} more")
            print()

    # ── Score ─────────────────────────────────────────────────
    secured_ratio = stats["endpoints_secured"] / max(stats["endpoints_found"], 1) * 100
    scoped_ratio = stats["endpoints_scoped"] / max(stats["endpoints_found"], 1) * 100

    score = 100
    if findings["HIGH"]:
        score -= len(findings["HIGH"]) * 5
    if findings["MEDIUM"]:
        score -= len(findings["MEDIUM"]) * 2
    if secured_ratio < 80:
        score -= (80 - secured_ratio) * 0.5
    if scoped_ratio < 70:
        score -= (70 - scoped_ratio) * 0.5
    score = max(0, min(100, score))

    print(f"  {'─'*60}")
    print(f"  SECURITY SCORE: {score:.0f}/100")
    print(f"  RBAC Coverage:  {secured_ratio:.0f}%")
    print(f"  Scoping:        {scoped_ratio:.0f}%")
    print(f"  {'─'*60}\n")

    return score


if __name__ == "__main__":
    score = scan_all()
    # Exit non-zero if critical issues found
    if findings["HIGH"]:
        print("⚠️  HIGH severity issues found. Review before production deployment.\n")
        sys.exit(1)
    print("✅ No critical issues found.\n")
