"""Shared grading boundaries and utilities.

Single source of truth for grade calculations used across the system.
"""

from __future__ import annotations

# Grade boundaries (Kenyan-style A–E with points)
GRADE_BOUNDARIES = [
    (80, "A", 12), (75, "A-", 11), (70, "B+", 10),
    (65, "B", 9), (60, "B-", 8), (55, "C+", 7),
    (50, "C", 6), (45, "C-", 5), (40, "D+", 4),
    (35, "D", 3), (30, "D-", 2), (0, "E", 1),
]

# Simplified boundaries (letter-only, no points)
GRADE_LETTER_BOUNDARIES = [(t, letter) for t, letter, _ in GRADE_BOUNDARIES]


def grade_for(pct: float) -> tuple[str, int]:
    """Return (grade_letter, grade_points) for a percentage."""
    for threshold, letter, points in GRADE_BOUNDARIES:
        if pct >= threshold:
            return letter, points
    return "E", 1


def compute_grade_letter(percentage: float) -> str:
    """Return grade letter only."""
    for threshold, grade in GRADE_LETTER_BOUNDARIES:
        if percentage >= threshold:
            return grade
    return "E"


def compute_term_mean(total_percentage_sum: float, count: int) -> float:
    """Compute a student's overall mean percentage across subjects."""
    return round(total_percentage_sum / (count or 1), 2)
