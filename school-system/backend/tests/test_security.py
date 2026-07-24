"""Unit tests for security module — password hashing & JWT."""

import pytest
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        pw = "Str0ng!Pass"
        hashed = hash_password(pw)
        assert hashed != pw
        assert verify_password(pw, hashed) is True
        assert verify_password("wrong", hashed) is False

    def test_unique_salts(self):
        pw = "same-password"
        h1 = hash_password(pw)
        h2 = hash_password(pw)
        assert h1 != h2  # Argon2 uses random salt
        assert verify_password(pw, h1)
        assert verify_password(pw, h2)


class TestJWT:
    def test_access_token_roundtrip(self):
        token = create_access_token("user-123", extra={"role": "teacher"})
        payload = decode_token(token)
        assert payload["sub"] == "user-123"
        assert payload["role"] == "teacher"
        assert payload["type"] == "access"

    def test_refresh_token_roundtrip(self):
        token = create_refresh_token("user-456", jti="jti-abc")
        payload = decode_token(token)
        assert payload["sub"] == "user-456"
        assert payload["jti"] == "jti-abc"
        assert payload["type"] == "refresh"

    def test_invalid_token_raises(self):
        with pytest.raises(Exception):
            decode_token("not.a.valid.jwt")

    def test_expired_token_raises(self):
        from datetime import datetime, timedelta, timezone
        from jose import jwt as jose_jwt
        from app.core.config import settings

        payload = {
            "sub": "user",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            "type": "access",
        }
        expired = jose_jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        with pytest.raises(Exception):
            decode_token(expired)
