"""
Password hashing, with nothing beyond the standard library.

PBKDF2-HMAC-SHA256, a per-password salt, and a constant-time compare. The
stored form carries its own parameters — `pbkdf2_sha256$<rounds>$<salt>$<hash>`
— so the cost can be raised later without stranding the rows already written.
"""

import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ROUNDS = 240_000


def hash_password(password: str, *, salt: str | None = None, rounds: int = ROUNDS) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), rounds).hex()

    return f"{ALGORITHM}${rounds}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt, digest = stored.split("$")
        if algorithm != ALGORITHM:
            return False
        expected = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds)).hex()
    except (AttributeError, ValueError):
        return False

    return hmac.compare_digest(expected, digest)
