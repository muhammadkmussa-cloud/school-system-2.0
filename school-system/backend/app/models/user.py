"""School Management System — User & Login History models."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    school_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("schools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    username: Mapped[str | None] = mapped_column(
        String(100), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True
    )
    phone: Mapped[str | None] = mapped_column(String(30))

    # Account lifecycle
    status: Mapped[str] = mapped_column(
        String(30), default="pending_first_login", nullable=False, index=True
    )
    # "pending_first_login" | "active" | "locked" | "disabled"
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    terms_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    profile_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Auth tracking
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_attempts: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    refresh_token_jti: Mapped[str | None] = mapped_column(String(100))

    # ── Backward-compat computed properties ──────────────────────
    @property
    def is_active(self) -> bool:
        return self.status in ("active", "pending_first_login")

    @property
    def is_verified(self) -> bool:
        return not self.must_change_password

    # relationships
    school = relationship("School", back_populates="users")
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False)
    login_history = relationship("LoginHistory", back_populates="user", lazy="dynamic")
    password_history = relationship("PasswordHistory", back_populates="user", lazy="dynamic")


class LoginHistory(Base):
    __tablename__ = "login_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user = relationship("User", back_populates="login_history")


class PasswordHistory(Base):
    __tablename__ = "password_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", back_populates="password_history")
