"""Auth schemas — login, token, password reset, first-login."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    school_code: str | None = Field(None, description="School code (optional)")
    username: str = Field(..., min_length=1, description="Teacher's username or email")
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserOut"
    must_change_password: bool = False
    account_status: str = "active"


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class FirstLoginRequest(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=128)
    email: EmailStr | None = None
    phone: str | None = None
    accept_terms: bool = False


class AccountStatusResponse(BaseModel):
    id: str
    username: str | None = None
    email: str
    full_name: str
    role: str
    status: str
    must_change_password: bool
    terms_accepted: bool
    profile_completed: bool
    last_login_at: str | None = None
    failed_login_attempts: int
    is_active: bool


from app.schemas.user import UserOut  # noqa: E402, F811
