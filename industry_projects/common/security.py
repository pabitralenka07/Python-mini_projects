"""Educational Authentication Simulation Helpers.

IMPORTANT NOTICE:
This module is strictly an educational simulation for teaching intermediate
Python concepts (hashing, salting, rate-limiting, and timing-attack prevention).
It is NOT a production-ready authentication library. Real production systems
must rely on vetted identity frameworks, industry-standard algorithms (such as
argon2id or bcrypt), multi-factor authentication, and robust credential vaults.
"""

import getpass
import hashlib
import hmac
import secrets
from datetime import UTC, datetime


def generate_salt(length: int = 16) -> bytes:
    """Generate cryptographically secure random salt."""
    return secrets.token_bytes(length)


def hash_secret(secret: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    """Hash a secret (password or PIN) using hashlib.scrypt with a random per-user salt.

    Returns:
        (hash_bytes, salt_bytes)
    """
    if salt is None:
        salt = generate_salt(16)

    derived = hashlib.scrypt(
        secret.encode("utf-8"),
        salt=salt,
        n=16384,
        r=8,
        p=1,
        maxmem=32 * 1024 * 1024,
    )
    return derived, salt


def verify_secret(secret: str, salt: bytes, expected_hash: bytes) -> bool:
    """Verify secret against expected hash in constant time using hmac.compare_digest."""
    actual_hash, _ = hash_secret(secret, salt=salt)
    return hmac.compare_digest(actual_hash, expected_hash)


def prompt_password(prompt: str = "Enter Password: ") -> str:
    """Safely prompt for secret entry without echoing characters."""
    try:
        val = getpass.getpass(prompt)
    except (EOFError, KeyboardInterrupt):
        raise
    except (getpass.GetPassWarning, OSError):
        val = input(prompt)
    return val.strip()


def is_locked(locked_until_iso: str | None, current_time_iso: str | None = None) -> bool:
    """Check if an account or card is currently locked out."""
    if not locked_until_iso:
        return False
    try:
        locked_until = datetime.fromisoformat(locked_until_iso)
        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=UTC)

        if current_time_iso:
            current_time = datetime.fromisoformat(current_time_iso)
            if current_time.tzinfo is None:
                current_time = current_time.replace(tzinfo=UTC)
        else:
            current_time = datetime.now(UTC)

        return current_time < locked_until
    except (ValueError, TypeError):
        return False
