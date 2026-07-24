"""Tests for the Student Results Engine."""

import pytest

from app.core.grading import grade_for, GRADE_BOUNDARIES


class TestGradeBoundaries:
    def test_grade_a(self):
        letter, points = grade_for(85)
        assert letter == "A"
        assert points == 12

    def test_grade_a_minus(self):
        letter, points = grade_for(77)
        assert letter == "A-"
        assert points == 11

    def test_grade_b_plus(self):
        letter, points = grade_for(72)
        assert letter == "B+"
        assert points == 10

    def test_grade_c(self):
        letter, points = grade_for(50)
        assert letter == "C"
        assert points == 6

    def test_grade_e(self):
        letter, points = grade_for(15)
        assert letter == "E"
        assert points == 1

    def test_all_thresholds(self):
        """Every boundary returns the correct grade."""
        for threshold, expected_letter, expected_points in GRADE_BOUNDARIES:
            letter, points = grade_for(float(threshold))
            assert letter == expected_letter, f"At {threshold}%, expected {expected_letter}"
            assert points == expected_points

    def test_just_above_threshold(self):
        letter, _ = grade_for(80.01)
        assert letter == "A"

    def test_just_below_threshold(self):
        letter, _ = grade_for(79.99)
        assert letter == "A-"


class TestResultsEngineHelpers:
    """Validate the grading engine's auxiliary functions."""

    def test_grade_for_zero(self):
        letter, points = grade_for(0)
        assert letter == "E"
        assert points == 1

    def test_grade_for_100(self):
        letter, points = grade_for(100)
        assert letter == "A"
        assert points == 12
