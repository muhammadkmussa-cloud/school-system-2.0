"""School Management System — Curriculum Service.

Provides curriculum-aware grading, level progression, and subject mapping.
Every school links to one curriculum which governs all grading logic.

Pre-loaded curricula: CBC Kenya, 8-4-4 Kenya, Cambridge IGCSE, IB, Nigeria BEC, South Africa CAPS.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.curriculum import Curriculum, CurriculumLevel, GradingScheme, GradeBand, SchoolCurriculum


# ── Pre-loaded curricula ────────────────────────────────────────────

BUILTIN_CURRICULA: list[dict] = [
    {
        "name": "CBC Kenya",
        "code": "CBC-KE",
        "country": "Kenya",
        "description": "Competency-Based Curriculum (2-6-3-3-3 system)",
        "levels": [
            {"name": "Pre-Primary 1", "code": "PP1", "order": 0, "terminal": False},
            {"name": "Pre-Primary 2", "code": "PP2", "order": 1, "terminal": False},
            {"name": "Grade 1", "code": "G1", "order": 2, "terminal": False},
            {"name": "Grade 2", "code": "G2", "order": 3, "terminal": False},
            {"name": "Grade 3", "code": "G3", "order": 4, "terminal": False},
            {"name": "Grade 4", "code": "G4", "order": 5, "terminal": False},
            {"name": "Grade 5", "code": "G5", "order": 6, "terminal": False},
            {"name": "Grade 6", "code": "G6", "order": 7, "terminal": False},
            {"name": "Grade 7", "code": "G7", "order": 8, "terminal": False},
            {"name": "Grade 8", "code": "G8", "order": 9, "terminal": False},
            {"name": "Grade 9", "code": "G9", "order": 10, "terminal": False},
            {"name": "Grade 10", "code": "G10", "order": 11, "terminal": False},
            {"name": "Grade 11", "code": "G11", "order": 12, "terminal": False},
            {"name": "Grade 12", "code": "G12", "order": 13, "terminal": True},
        ],
        "grading": {
            "name": "CBC Standard",
            "bands": [
                ("E", 0, 39, 1, "Below Expectation"),
                ("D", 40, 49, 2, "Approaches Expectation"),
                ("C", 50, 64, 3, "Meets Expectation"),
                ("B", 65, 79, 4, "Exceeds Expectation"),
                ("A", 80, 100, 5, "Outstanding"),
            ],
        },
    },
    {
        "name": "8-4-4 Kenya",
        "code": "844-KE",
        "country": "Kenya",
        "description": "Traditional 8-4-4 system (phasing out)",
        "levels": [
            {"name": "Standard 1", "code": "STD1", "order": 1, "terminal": False},
            {"name": "Standard 2", "code": "STD2", "order": 2, "terminal": False},
            {"name": "Standard 3", "code": "STD3", "order": 3, "terminal": False},
            {"name": "Standard 4", "code": "STD4", "order": 4, "terminal": False},
            {"name": "Standard 5", "code": "STD5", "order": 5, "terminal": False},
            {"name": "Standard 6", "code": "STD6", "order": 6, "terminal": False},
            {"name": "Standard 7", "code": "STD7", "order": 7, "terminal": False},
            {"name": "Standard 8", "code": "STD8", "order": 8, "terminal": True},
            {"name": "Form 1", "code": "F1", "order": 9, "terminal": False},
            {"name": "Form 2", "code": "F2", "order": 10, "terminal": False},
            {"name": "Form 3", "code": "F3", "order": 11, "terminal": False},
            {"name": "Form 4", "code": "F4", "order": 12, "terminal": True},
        ],
        "grading": {
            "name": "KCSE Standard (A-E)",
            "bands": [
                ("E", 0, 29, 1, "Fail"),
                ("D-", 30, 34, 2, "Poor"),
                ("D", 35, 39, 3, "Below Average"),
                ("D+", 40, 44, 4, "Below Average"),
                ("C-", 45, 49, 5, "Average"),
                ("C", 50, 54, 6, "Average"),
                ("C+", 55, 59, 7, "Above Average"),
                ("B-", 60, 64, 8, "Good"),
                ("B", 65, 69, 9, "Good"),
                ("B+", 70, 74, 10, "Very Good"),
                ("A-", 75, 79, 11, "Excellent"),
                ("A", 80, 100, 12, "Outstanding"),
            ],
        },
    },
    {
        "name": "Cambridge IGCSE",
        "code": "CAM-IGCSE",
        "country": "International",
        "description": "Cambridge International IGCSE",
        "levels": [
            {"name": "Year 7", "code": "Y7", "order": 1, "terminal": False},
            {"name": "Year 8", "code": "Y8", "order": 2, "terminal": False},
            {"name": "Year 9", "code": "Y9", "order": 3, "terminal": False},
            {"name": "Year 10", "code": "Y10", "order": 4, "terminal": False},
            {"name": "Year 11", "code": "Y11", "order": 5, "terminal": True},
            {"name": "Year 12", "code": "Y12", "order": 6, "terminal": False},
            {"name": "Year 13", "code": "Y13", "order": 7, "terminal": True},
        ],
        "grading": {
            "name": "IGCSE A*-G",
            "bands": [
                ("G", 0, 19, 1, "Ungraded"),
                ("F", 20, 29, 2, "Marginal"),
                ("E", 30, 39, 3, "Satisfactory"),
                ("D", 40, 49, 4, "Fair"),
                ("C", 50, 59, 5, "Good"),
                ("B", 60, 69, 6, "Very Good"),
                ("A", 70, 79, 7, "Excellent"),
                ("A*", 80, 100, 8, "Outstanding"),
            ],
        },
    },
    {
        "name": "IB Diploma",
        "code": "IB-DP",
        "country": "International",
        "description": "International Baccalaureate Diploma Programme",
        "levels": [
            {"name": "DP Year 1", "code": "DP1", "order": 1, "terminal": False},
            {"name": "DP Year 2", "code": "DP2", "order": 2, "terminal": True},
        ],
        "grading": {
            "name": "IB 1-7 Scale",
            "bands": [
                ("1", 0, 14, 1, "Very Poor"),
                ("2", 15, 27, 2, "Poor"),
                ("3", 28, 39, 2, "Mediocre"),
                ("4", 40, 54, 3, "Satisfactory"),
                ("5", 55, 69, 4, "Good"),
                ("6", 70, 84, 5, "Very Good"),
                ("7", 85, 100, 7, "Excellent"),
            ],
        },
    },
    {
        "name": "Nigeria BEC",
        "code": "NG-BEC",
        "country": "Nigeria",
        "description": "Basic Education Curriculum (9-3-4 system)",
        "levels": [
            {"name": "Primary 1", "code": "P1", "order": 1, "terminal": False},
            {"name": "Primary 2", "code": "P2", "order": 2, "terminal": False},
            {"name": "Primary 3", "code": "P3", "order": 3, "terminal": False},
            {"name": "Primary 4", "code": "P4", "order": 4, "terminal": False},
            {"name": "Primary 5", "code": "P5", "order": 5, "terminal": False},
            {"name": "Primary 6", "code": "P6", "order": 6, "terminal": True},
            {"name": "JSS 1", "code": "JSS1", "order": 7, "terminal": False},
            {"name": "JSS 2", "code": "JSS2", "order": 8, "terminal": False},
            {"name": "JSS 3", "code": "JSS3", "order": 9, "terminal": True},
            {"name": "SSS 1", "code": "SSS1", "order": 10, "terminal": False},
            {"name": "SSS 2", "code": "SSS2", "order": 11, "terminal": False},
            {"name": "SSS 3", "code": "SSS3", "order": 12, "terminal": True},
        ],
        "grading": {
            "name": "WAEC A1-F9",
            "bands": [
                ("F9", 0, 34, 1, "Fail"),
                ("E8", 35, 39, 2, "Pass"),
                ("D7", 40, 44, 3, "Pass"),
                ("C6", 45, 49, 4, "Credit"),
                ("C5", 50, 54, 5, "Credit"),
                ("C4", 55, 59, 5, "Credit"),
                ("B3", 60, 69, 6, "Good"),
                ("B2", 70, 79, 7, "Very Good"),
                ("A1", 80, 100, 8, "Excellent"),
            ],
        },
    },
    {
        "name": "South Africa CAPS",
        "code": "ZA-CAPS",
        "country": "South Africa",
        "description": "Curriculum and Assessment Policy Statement",
        "levels": [
            {"name": "Grade R", "code": "GR", "order": 0, "terminal": False},
            {"name": "Grade 1", "code": "G1", "order": 1, "terminal": False},
            {"name": "Grade 2", "code": "G2", "order": 2, "terminal": False},
            {"name": "Grade 3", "code": "G3", "order": 3, "terminal": False},
            {"name": "Grade 4", "code": "G4", "order": 4, "terminal": False},
            {"name": "Grade 5", "code": "G5", "order": 5, "terminal": False},
            {"name": "Grade 6", "code": "G6", "order": 6, "terminal": False},
            {"name": "Grade 7", "code": "G7", "order": 7, "terminal": False},
            {"name": "Grade 8", "code": "G8", "order": 8, "terminal": False},
            {"name": "Grade 9", "code": "G9", "order": 9, "terminal": False},
            {"name": "Grade 10", "code": "G10", "order": 10, "terminal": False},
            {"name": "Grade 11", "code": "G11", "order": 11, "terminal": False},
            {"name": "Grade 12", "code": "G12", "order": 12, "terminal": True},
        ],
        "grading": {
            "name": "CAPS Levels 1-7",
            "bands": [
                ("1", 0, 29, 1, "Not Achieved"),
                ("2", 30, 39, 2, "Elementary"),
                ("3", 40, 49, 3, "Moderate"),
                ("4", 50, 59, 4, "Adequate"),
                ("5", 60, 69, 5, "Substantial"),
                ("6", 70, 79, 6, "Meritorious"),
                ("7", 80, 100, 7, "Outstanding"),
            ],
        },
    },
]


class CurriculumService:
    """Manages curricula, grading, and school-curriculum links."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Seeding ──────────────────────────────────────────────────

    async def seed_builtin_curricula(self) -> int:
        """Insert all BUILTIN_CURRICULA if they don't exist. Returns count seeded."""
        count = 0
        for data in BUILTIN_CURRICULA:
            exists = await self.db.scalar(
                select(Curriculum).where(Curriculum.code == data["code"])
            )
            if exists:
                continue

            curr = Curriculum(
                name=data["name"],
                code=data["code"],
                country=data.get("country"),
                description=data.get("description"),
            )
            self.db.add(curr)
            await self.db.flush()

            # Levels
            for lvl in data["levels"]:
                self.db.add(CurriculumLevel(
                    curriculum_id=curr.id,
                    name=lvl["name"],
                    code=lvl["code"],
                    sort_order=lvl["order"],
                    is_terminal=lvl["terminal"],
                ))

            # Grading scheme
            gs_data = data["grading"]
            scheme = GradingScheme(
                curriculum_id=curr.id,
                name=gs_data["name"],
                is_default=True,
            )
            self.db.add(scheme)
            await self.db.flush()

            for band in gs_data["bands"]:
                letter, lo, hi, pts, remark = band
                self.db.add(GradeBand(
                    scheme_id=scheme.id,
                    letter=letter,
                    min_percentage=float(lo),
                    max_percentage=float(hi),
                    points=pts,
                    remark=remark,
                ))

            count += 1

        await self.db.flush()
        return count

    # ── Queries ──────────────────────────────────────────────────

    async def list_curricula(self, active_only: bool = True) -> list[Curriculum]:
        stmt = select(Curriculum)
        if active_only:
            stmt = stmt.where(Curriculum.is_active == True)
        return list((await self.db.scalars(stmt.order_by(Curriculum.name))).all())

    async def get_curriculum(self, curriculum_id: uuid.UUID) -> Curriculum | None:
        return await self.db.scalar(select(Curriculum).where(Curriculum.id == curriculum_id))

    async def get_levels(self, curriculum_id: uuid.UUID) -> list[CurriculumLevel]:
        rows = await self.db.scalars(
            select(CurriculumLevel)
            .where(CurriculumLevel.curriculum_id == curriculum_id)
            .order_by(CurriculumLevel.sort_order)
        )
        return list(rows)

    async def get_grading_scheme(self, curriculum_id: uuid.UUID) -> GradingScheme | None:
        return await self.db.scalar(
            select(GradingScheme).where(
                GradingScheme.curriculum_id == curriculum_id,
                GradingScheme.is_default == True,
            )
        )

    async def get_grade_bands(self, scheme_id: uuid.UUID) -> list[GradeBand]:
        rows = await self.db.scalars(
            select(GradeBand)
            .where(GradeBand.scheme_id == scheme_id)
            .order_by(GradeBand.min_percentage.desc())
        )
        return list(rows)

    async def grade_for(self, curriculum_id: uuid.UUID, percentage: float) -> tuple[str, int, str]:
        """Return (letter, points, remark) for a percentage under this curriculum."""
        scheme = await self.get_grading_scheme(curriculum_id)
        if not scheme:
            return ("N/A", 0, "")

        bands = await self.get_grade_bands(scheme.id)
        for band in bands:
            if band.min_percentage <= percentage <= band.max_percentage:
                return band.letter, band.points, band.remark or ""

        return ("N/A", 0, "")

    async def assign_school_curriculum(
        self, school_id: uuid.UUID, curriculum_id: uuid.UUID
    ) -> SchoolCurriculum:
        """Assign a curriculum to a school (deactivates previous)."""
        # Deactivate existing
        existing = await self.db.scalars(
            select(SchoolCurriculum).where(
                SchoolCurriculum.school_id == school_id,
                SchoolCurriculum.is_active == True,
            )
        )
        for sc in existing:
            sc.is_active = False

        sc = SchoolCurriculum(
            school_id=school_id,
            curriculum_id=curriculum_id,
            is_active=True,
        )
        self.db.add(sc)
        await self.db.flush()
        await self.db.refresh(sc)
        return sc

    async def get_school_curriculum(self, school_id: uuid.UUID) -> Curriculum | None:
        sc = await self.db.scalar(
            select(SchoolCurriculum).where(
                SchoolCurriculum.school_id == school_id,
                SchoolCurriculum.is_active == True,
            )
        )
        if not sc:
            return None
        return await self.get_curriculum(sc.curriculum_id)

    async def get_promotion_path(
        self, school_id: uuid.UUID, current_level_code: str
    ) -> list[dict]:
        """Get promotion chain for a given level code."""
        curriculum = await self.get_school_curriculum(school_id)
        if not curriculum:
            return []

        levels = await self.get_levels(curriculum.id)

        found = False
        chain = []
        for lvl in levels:
            if lvl.code == current_level_code:
                found = True
            if found:
                chain.append({
                    "code": lvl.code,
                    "name": lvl.name,
                    "order": lvl.sort_order,
                    "is_terminal": lvl.is_terminal,
                })
            if found and lvl.is_terminal:
                break

        return chain if found else []


# ── Singleton for seeding (called at startup) ───────────────────────

async def seed_all_curricula(db: AsyncSession) -> None:
    svc = CurriculumService(db)
    count = await svc.seed_builtin_curricula()
    if count:
        from loguru import logger
        logger.info(f"🌍 Seeded {count} curricula")
