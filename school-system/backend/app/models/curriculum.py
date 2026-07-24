"""School Management System — Curriculum models.

Schools can configure any curriculum (CBC, 8-4-4, Cambridge, IGCSE, IB, etc.)
with configurable levels, subjects, and grading schemes.

A curriculum defines:
- Name & description
- Level hierarchy (e.g. Grade 1→12, Form 1→4, Year 1→13)
- Subject categories
- Grading scheme (A–E, 1–9, percentage bands, etc.)
- Promotion rules
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Curriculum(Base, TimestampMixin):
    """A named curriculum framework (e.g. 'CBC Kenya', 'Cambridge IGCSE')."""
    __tablename__ = "curricula"

    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(String(100))  # country of origin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_: Mapped[dict | None] = mapped_column(JSON, name="metadata")  # extra config

    levels = relationship("CurriculumLevel", back_populates="curriculum", lazy="dynamic",
                          cascade="all, delete-orphan", order_by="CurriculumLevel.sort_order")
    grading_schemes = relationship("GradingScheme", back_populates="curriculum", lazy="dynamic",
                                   cascade="all, delete-orphan")


class CurriculumLevel(Base, TimestampMixin):
    """A level/grade within a curriculum (e.g. 'Form 1', 'Grade 7', 'Year 10')."""
    __tablename__ = "curriculum_levels"
    __table_args__ = (
        UniqueConstraint("curriculum_id", "code", name="uq_curriculum_level_code"),
    )

    curriculum_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)  # 1, 2, 3...
    description: Mapped[str | None] = mapped_column(Text)
    is_terminal: Mapped[bool] = mapped_column(
        Boolean, default=False
    )  # True = final year (graduates from here)
    promotion_to_level_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True)
    )  # explicit next level (null = auto-infer from sort_order)

    curriculum = relationship("Curriculum", back_populates="levels")


class GradingScheme(Base, TimestampMixin):
    """A grading system (e.g. A–E, 1–9, percentage-based, custom)."""
    __tablename__ = "grading_schemes"

    curriculum_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    curriculum = relationship("Curriculum", back_populates="grading_schemes")
    bands = relationship("GradeBand", back_populates="scheme", lazy="dynamic",
                         cascade="all, delete-orphan", order_by="GradeBand.min_percentage.desc()")


class GradeBand(Base, TimestampMixin):
    """A single grade band within a scheme (e.g. A: 80–100, points=12)."""
    __tablename__ = "grade_bands"

    scheme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("grading_schemes.id", ondelete="CASCADE"), nullable=False
    )
    letter: Mapped[str] = mapped_column(String(5), nullable=False)  # "A", "A-", "B+"
    min_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    max_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=1)
    remark: Mapped[str | None] = mapped_column(String(200))  # "Excellent", "Good"

    scheme = relationship("GradingScheme", back_populates="bands")


class SchoolCurriculum(Base, TimestampMixin):
    """Links a school to a curriculum with optional overrides."""
    __tablename__ = "school_curricula"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    curriculum_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("curricula.id", ondelete="CASCADE"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    config_overrides: Mapped[dict | None] = mapped_column(JSON)  # school-specific tweaks
