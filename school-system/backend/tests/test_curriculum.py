"""Tests for the Curriculum service — grading, levels, seeding."""

import pytest

from app.services.curriculum.curriculum_service import (
    BUILTIN_CURRICULA,
    CurriculumService,
)


class TestCurriculaData:
    """Validate built-in curriculum definitions."""

    def test_all_curricula_have_required_fields(self):
        for c in BUILTIN_CURRICULA:
            assert "name" in c
            assert "code" in c
            assert "levels" in c
            assert "grading" in c
            assert len(c["levels"]) > 0

    def test_curricula_have_unique_codes(self):
        codes = [c["code"] for c in BUILTIN_CURRICULA]
        assert len(codes) == len(set(codes)), "Duplicate curriculum codes"

    def test_cbc_has_14_levels(self):
        cbc = [c for c in BUILTIN_CURRICULA if c["code"] == "CBC-KE"][0]
        assert len(cbc["levels"]) == 14  # PP1 → G12

    def test_844_has_12_levels(self):
        kcse = [c for c in BUILTIN_CURRICULA if c["code"] == "844-KE"][0]
        assert len(kcse["levels"]) == 12  # STD1 → F4

    def test_igcse_has_7_levels(self):
        igcse = [c for c in BUILTIN_CURRICULA if c["code"] == "CAM-IGCSE"][0]
        assert len(igcse["levels"]) == 7  # Y7 → Y13

    def test_ib_has_2_levels(self):
        ib = [c for c in BUILTIN_CURRICULA if c["code"] == "IB-DP"][0]
        assert len(ib["levels"]) == 2

    def test_last_level_is_terminal(self):
        for c in BUILTIN_CURRICULA:
            last = c["levels"][-1]
            assert last["terminal"] is True, f"{c['code']}: last level should be terminal"

    def test_first_level_not_terminal(self):
        for c in BUILTIN_CURRICULA:
            first = c["levels"][0]
            # PP1 is terminal = False
            assert first["terminal"] is False or first["order"] == 0


class TestGradingSchemes:
    """Validate grading schemes in built-in curricula."""

    def test_all_have_grading_bands(self):
        for c in BUILTIN_CURRICULA:
            bands = c["grading"]["bands"]
            assert len(bands) > 0
            # Each band: (letter, min, max, points, remark)
            for band in bands:
                assert len(band) == 5
                assert isinstance(band[1], (int, float))
                assert isinstance(band[2], (int, float))
                assert band[1] <= band[2]

    def test_kcse_has_12_bands(self):
        kcse = [c for c in BUILTIN_CURRICULA if c["code"] == "844-KE"][0]
        assert len(kcse["grading"]["bands"]) == 12  # E → A

    def test_cbc_has_5_bands(self):
        cbc = [c for c in BUILTIN_CURRICULA if c["code"] == "CBC-KE"][0]
        assert len(cbc["grading"]["bands"]) == 5  # E → A

    def test_ib_has_7_bands(self):
        ib = [c for c in BUILTIN_CURRICULA if c["code"] == "IB-DP"][0]
        assert len(ib["grading"]["bands"]) == 7  # 1 → 7

    def test_bands_cover_0_to_100(self):
        for c in BUILTIN_CURRICULA:
            bands = c["grading"]["bands"]
            min_pct = min(b[1] for b in bands)
            max_pct = max(b[2] for b in bands)
            assert min_pct == 0, f"{c['code']}: min should be 0"
            assert max_pct >= 100, f"{c['code']}: max should be >= 100"


class TestCurriculumService:
    """Test CurriculumService logic that doesn't need a DB."""

    def test_grade_boundaries_no_gaps(self):
        """Grading bands should have no gaps between 0 and 100."""
        for c in BUILTIN_CURRICULA:
            bands = sorted(c["grading"]["bands"], key=lambda b: b[1])
            for i in range(len(bands) - 1):
                gap = bands[i + 1][1] - bands[i][2]
                # Allow 1-point gap at boundaries
                assert gap <= 1, (
                    f"{c['code']}: gap of {gap} between '{bands[i][0]}' "
                    f"(max {bands[i][2]}) and '{bands[i+1][0]}' (min {bands[i+1][1]})"
                )

    def test_points_descending_with_grade(self):
        """Higher grades should have more points."""
        for c in BUILTIN_CURRICULA:
            bands = sorted(c["grading"]["bands"], key=lambda b: b[1])
            for i in range(len(bands) - 1):
                assert bands[i + 1][3] >= bands[i][3], (
                    f"{c['code']}: points should not decrease"
                )
