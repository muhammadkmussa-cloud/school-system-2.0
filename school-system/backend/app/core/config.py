"""School Management System — Central Configuration.

All settings are loaded from environment variables with sensible defaults
for local development. In production, override via the runtime environment.
"""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import Literal

from pydantic import (
    AnyHttpUrl,
    EmailStr,
    PostgresDsn,
    ValidationInfo,
    field_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────
    APP_NAME: str = "School Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

    # ── Server ───────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    CORS_ORIGINS: list[AnyHttpUrl] = []

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    # ── Database ─────────────────────────────────────────────────────
    DATABASE_URL: PostgresDsn = "postgresql+asyncpg://postgres:postgres@localhost:5432/school_system"

    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_RECYCLE: int = 3600
    DB_ECHO: bool = False

    # ── Redis ────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── JWT / Auth ───────────────────────────────────────────────────
    # IMPORTANT: Set SECRET_KEY in .env for production. The fallback
    # generates a new key each start, invalidating all existing tokens.
    SECRET_KEY: str = secrets.token_urlsafe(64)
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    REFRESH_TOKEN_ROTATION: bool = True

    # ── Argon2 ───────────────────────────────────────────────────────
    ARGON2_TIME_COST: int = 2
    ARGON2_MEMORY_COST: int = 19456  # ~19 MiB
    ARGON2_PARALLELISM: int = 1
    ARGON2_HASH_LEN: int = 32
    ARGON2_SALT_LEN: int = 16

    # ── S3-Compatible Storage ────────────────────────────────────────
    S3_ENDPOINT: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "school-system-uploads"
    S3_REGION: str = "auto"
    S3_PUBLIC_URL: str = ""

    # ── Email (optional) ─────────────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: EmailStr | str = "noreply@example.com"
    SMTP_TLS: bool = True

    # ── Limits ───────────────────────────────────────────────────────
    MAX_SCHOOLS_PER_INSTANCE: int = 500
    MAX_STUDENTS_PER_SCHOOL: int = 5000
    MAX_TEACHERS_PER_SCHOOL: int = 200
    MAX_FILE_UPLOAD_MB: int = 10
    SESSION_IDLE_TIMEOUT_MINUTES: int = 60
    FAILED_LOGIN_LOCKOUT: int = 5
    FAILED_LOGIN_WINDOW_MINUTES: int = 15

    # ── Offline Sync ─────────────────────────────────────────────────
    OFFLINE_SYNC_BATCH_SIZE: int = 2000

    # ── API Limits ───────────────────────────────────────────────────
    MOBILE_STUDENT_LIST_LIMIT: int = 500
    AUDIT_RECENT_LIMIT: int = 100

    # ── Payment Gateways ─────────────────────────────────────────────
    MPESA_TIMEOUT_SECONDS: int = 15
    MPESA_QUERY_TIMEOUT_SECONDS: int = 30
    PAYSTACK_TIMEOUT_SECONDS: int = 15
    PAYSTACK_SIGNATURE_HEADER: str = "x-paystack-signature"


settings = Settings()
