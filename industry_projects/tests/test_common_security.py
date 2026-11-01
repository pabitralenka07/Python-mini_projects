"""Tests for common.security module."""

from common.security import hash_secret, is_locked, verify_secret


def test_hash_and_verify_secret() -> None:
    secret = "secret123"
    hashed, salt = hash_secret(secret)
    assert isinstance(hashed, bytes)
    assert isinstance(salt, bytes)
    assert verify_secret(secret, salt, hashed) is True
    assert verify_secret("wrong_secret", salt, hashed) is False


def test_is_locked() -> None:
    # Future lockout
    assert is_locked("2099-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00") is True
    # Past lockout
    assert is_locked("2020-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00") is False
    # None lockout
    assert is_locked(None) is False
