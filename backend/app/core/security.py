"""
Kryptografiske primitiver (SEC-01, SEC-02).

- Argon2id til kunde-adgangskoder.
- Tilfældige session-tokens; kun SHA-256-hash gemmes server-side.
- CSRF-token-generering.

AD-passwords håndteres ALDRIG her - de sendes kun videre til LDAPS-bind
og gemmes aldrig (AD-02).
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

# Argon2id med fornuftige parametre til et lab/demo-miljø.
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=64 * 1024,   # 64 MB
    parallelism=2,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    """Hash en kunde-adgangskode med Argon2id (SEC-01)."""
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verificér en adgangskode mod et gemt Argon2id-hash."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """Om et hash bør opdateres (f.eks. ændrede parametre)."""
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def generate_session_token() -> str:
    """Kryptografisk tilfældigt session-token (gives til klienten i cookie)."""
    return secrets.token_urlsafe(48)


def generate_csrf_token() -> str:
    """Tilfældigt CSRF-token (SEC-03)."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """
    SEC-02: tokens gemmes kun som hash server-side.
    SHA-256 er passende her, da tokens er høj-entropi tilfældige værdier
    (ikke lav-entropi passwords, som kræver Argon2).
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    """Tidskonstant sammenligning (CSRF/token-tjek)."""
    return hmac.compare_digest(a, b)
