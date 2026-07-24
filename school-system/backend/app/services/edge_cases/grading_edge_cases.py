"""School Management System — Grading Edge-Case Handler.

Ensures the results engine handles real-world edge cases correctly:
- Tie-breaking in rankings (same mean → same rank, skip next)
- Empty assessments (no marks yet → graceful zero)
- Negative / out-of-range scores → clamped
- Single-student classes
- All absences (every student absent from an exam)
- Decimal precision consistency
"""

from __future__ import annotations


def resolve_ties(rankings: list[dict]) -> list[dict]:
    """Apply standard competition ranking (1224) to a sorted list.

    If two students tie at position 1, both get rank 1, next gets rank 3.
    """
    if not rankings:
        return rankings

    rankings.sort(key=lambda r: r.get("mean", 0), reverse=True)

    current_rank = 1
    i = 0
    while i < len(rankings):
        # Find all students with this same mean
        j = i
        while j < len(rankings) and rankings[j].get("mean") == rankings[i].get("mean"):
            rankings[j]["rank"] = current_rank
            j += 1
        tied_count = j - i
        current_rank += tied_count
        i = j

    return rankings


def clamp_score(score: float, max_score: float) -> float:
    """Clamp a score to [0, max_score]. Negative → 0. Over max → max."""
    return max(0.0, min(float(score), float(max_score)))


def safe_percentage(score: float, max_score: float) -> float:
    """Return a percentage safely. 0/0 → 0.0. Negative scores → 0%."""
    score = clamp_score(score, max_score)
    if max_score <= 0:
        return 0.0
    return round((score / max_score) * 100, 2)


def weighted_aggregate(
    assessments: list[tuple[float, float, float]],  # (score, max_score, weight)
) -> dict:
    """Aggregate weighted scores safely.

    Returns {"total": float, "max_possible": float, "percentage": float}
    """
    total = 0.0
    max_possible = 0.0

    for score, max_s, weight in assessments:
        score = clamp_score(score, max_s)
        weight = max(0.0, weight)
        total += score * weight
        max_possible += max_s * weight

    if max_possible <= 0:
        return {"total": 0.0, "max_possible": 0.0, "percentage": 0.0}

    return {
        "total": round(total, 2),
        "max_possible": round(max_possible, 2),
        "percentage": round((total / max_possible) * 100, 2),
    }


def validate_assessment(assessment: dict) -> list[str]:
    """Validate an assessment configuration. Returns list of issues."""
    issues = []

    name = assessment.get("name", "")
    if not name or not name.strip():
        issues.append("Assessment name is required")

    max_score = assessment.get("max_score", 0)
    if max_score <= 0:
        issues.append(f"max_score must be positive (got {max_score})")

    weight = assessment.get("weight", 1.0)
    if weight < 0:
        issues.append(f"weight cannot be negative (got {weight})")

    assessment_type = assessment.get("assessment_type", "")
    valid_types = {"exam", "test", "quiz", "assignment", "project"}
    if assessment_type not in valid_types:
        issues.append(f"Unknown assessment_type '{assessment_type}'. Use: {valid_types}")

    return issues


def attendance_rate(present: int, total: int) -> float:
    """Safe attendance rate. 0/0 → 100% (no students = perfect attendance)."""
    if total <= 0:
        return 100.0
    return round((max(0, present) / total) * 100, 2)


def is_pass(percentage: float, pass_threshold: float = 35.0) -> bool:
    """Check if a percentage meets the pass threshold (default D- = 30%)."""
    return percentage >= pass_threshold
