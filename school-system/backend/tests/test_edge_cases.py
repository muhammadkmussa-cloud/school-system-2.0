"""Tests for Edge-Case Handlers — Grading & Ranking Robustness.

Validates tie-breaking, score clamping, safe percentage, weighted aggregation,
assessment validation, and attendance rate edge cases.
"""

import pytest
from app.services.edge_cases.grading_edge_cases import (
    resolve_ties,
    clamp_score,
    safe_percentage,
    weighted_aggregate,
    validate_assessment,
    attendance_rate,
    is_pass,
)


class TestTieBreaking:
    """Competition ranking (1224): ties share rank, next rank skips."""

    def test_no_ties(self):
        rankings = [
            {"name": "A", "mean": 90.0},
            {"name": "B", "mean": 85.0},
            {"name": "C", "mean": 80.0},
        ]
        result = resolve_ties(rankings)
        assert result[0]["rank"] == 1
        assert result[1]["rank"] == 2
        assert result[2]["rank"] == 3

    def test_two_way_tie_first(self):
        rankings = [
            {"name": "A", "mean": 85.0},
            {"name": "B", "mean": 85.0},
            {"name": "C", "mean": 80.0},
        ]
        result = resolve_ties(rankings)
        assert result[0]["rank"] == 1
        assert result[1]["rank"] == 1  # tied
        assert result[2]["rank"] == 3  # skipped rank 2

    def test_two_way_tie_middle(self):
        rankings = [
            {"name": "A", "mean": 90.0},
            {"name": "B", "mean": 80.0},
            {"name": "C", "mean": 80.0},
        ]
        result = resolve_ties(rankings)
        assert result[0]["rank"] == 1
        assert result[1]["rank"] == 2
        assert result[2]["rank"] == 2  # tied

    def test_three_way_tie(self):
        rankings = [
            {"name": "A", "mean": 75.0},
            {"name": "B", "mean": 75.0},
            {"name": "C", "mean": 75.0},
            {"name": "D", "mean": 70.0},
        ]
        result = resolve_ties(rankings)
        assert result[0]["rank"] == 1
        assert result[1]["rank"] == 1
        assert result[2]["rank"] == 1
        assert result[3]["rank"] == 4  # 1+3=4

    def test_all_tied(self):
        rankings = [{"name": "A", "mean": 50.0} for _ in range(5)]
        result = resolve_ties(rankings)
        assert all(r["rank"] == 1 for r in result)

    def test_empty_list(self):
        assert resolve_ties([]) == []

    def test_single_student(self):
        rankings = [{"name": "Only", "mean": 88.0}]
        result = resolve_ties(rankings)
        assert result[0]["rank"] == 1


class TestScoreClamping:
    """Scores are clamped to [0, max_score]."""

    def test_negative_becomes_zero(self):
        assert clamp_score(-5, 100) == 0.0

    def test_over_max(self):
        assert clamp_score(120, 100) == 100.0

    def test_normal(self):
        assert clamp_score(75, 100) == 75.0

    def test_zero(self):
        assert clamp_score(0, 100) == 0.0

    def test_perfect(self):
        assert clamp_score(100, 100) == 100.0

    def test_float_input(self):
        assert clamp_score(85.7, 100) == 85.7


class TestSafePercentage:
    """Percentage calculation handles edge cases gracefully."""

    def test_normal(self):
        assert safe_percentage(75, 100) == 75.0

    def test_zero_score(self):
        assert safe_percentage(0, 100) == 0.0

    def test_perfect_score(self):
        assert safe_percentage(100, 100) == 100.0

    def test_zero_max_returns_zero(self):
        assert safe_percentage(50, 0) == 0.0

    def test_negative_score_clamped(self):
        assert safe_percentage(-10, 100) == 0.0

    def test_negative_max(self):
        assert safe_percentage(50, -1) == 0.0


class TestWeightedAggregate:
    """Weighted aggregation with edge cases."""

    def test_single_assessment(self):
        result = weighted_aggregate([(80, 100, 1.0)])
        assert result["percentage"] == 80.0

    def test_multiple_weighted(self):
        # CAT 15%, Midterm 25%, Endterm 60%
        result = weighted_aggregate([
            (60, 100, 0.15),
            (70, 100, 0.25),
            (80, 100, 0.60),
        ])
        # (60*0.15 + 70*0.25 + 80*0.60) / (100*0.15 + 100*0.25 + 100*0.60)
        # = (9+17.5+48) / (15+25+60) = 74.5 / 100 = 74.5%
        assert result["percentage"] == 74.5

    def test_all_zero_scores(self):
        result = weighted_aggregate([(0, 100, 1.0), (0, 100, 1.0)])
        assert result["percentage"] == 0.0

    def test_empty_list(self):
        result = weighted_aggregate([])
        assert result["percentage"] == 0.0
        assert result["total"] == 0.0

    def test_zero_weight(self):
        result = weighted_aggregate([(90, 100, 0.0)])
        assert result["percentage"] == 0.0

    def test_negative_weight_ignored(self):
        result = weighted_aggregate([(80, 100, 1.0), (90, 100, -1.0)])
        # Only the first counts (negative weight → 0)
        assert result["percentage"] == 80.0


class TestValidateAssessment:
    """Assessment configuration validation."""

    def test_valid(self):
        issues = validate_assessment({
            "name": "Math Test", "max_score": 100,
            "weight": 1.0, "assessment_type": "exam",
        })
        assert len(issues) == 0

    def test_missing_name(self):
        issues = validate_assessment({"name": "", "max_score": 100})
        assert any("name" in i.lower() for i in issues)

    def test_zero_max_score(self):
        issues = validate_assessment({"name": "X", "max_score": 0})
        assert any("max_score" in i.lower() for i in issues)

    def test_negative_max_score(self):
        issues = validate_assessment({"name": "X", "max_score": -10})
        assert any("max_score" in i.lower() for i in issues)

    def test_invalid_type(self):
        issues = validate_assessment({"name": "X", "max_score": 50, "assessment_type": "unknown"})
        assert any("assessment_type" in i.lower() for i in issues)

    def test_valid_types_all(self):
        for t in ("exam", "test", "quiz", "assignment", "project"):
            issues = validate_assessment({"name": "X", "max_score": 50, "assessment_type": t})
            assert len(issues) == 0


class TestAttendanceRate:
    """Attendance rate edge cases."""

    def test_full_attendance(self):
        assert attendance_rate(20, 20) == 100.0

    def test_half(self):
        assert attendance_rate(10, 20) == 50.0

    def test_zero_students_perfect(self):
        assert attendance_rate(0, 0) == 100.0

    def test_negative_present(self):
        assert attendance_rate(-5, 20) == 0.0

    def test_large_numbers(self):
        rate = attendance_rate(875, 1000)
        assert rate == 87.5


class TestIsPass:
    """Pass/fail threshold logic."""

    def test_above_threshold(self):
        assert is_pass(50.0, 35.0) is True

    def test_below_threshold(self):
        assert is_pass(30.0, 35.0) is False

    def test_at_threshold(self):
        assert is_pass(35.0, 35.0) is True

    def test_default_threshold(self):
        assert is_pass(35.0) is True
        assert is_pass(34.9) is False
