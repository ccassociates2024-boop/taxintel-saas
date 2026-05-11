"""Fernet-backed PII encryption helpers.

encrypt_pii / decrypt_pii operate on plain strings.
EncryptedString is a SQLAlchemy TypeDecorator for transparent column-level
encryption — apply to clients.pan, clients.phone, clients.email, and any
token column that holds citizen PII.

Key management
--------------
Set PII_ENCRYPTION_KEY to a URL-safe base64-encoded 32-byte Fernet key:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

The key is read once at startup and cached. Rotation requires a data
migration that re-encrypts all rows using the new key.
"""

from __future__ import annotations

import os
import logging

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is not None:
        return _fernet

    raw = os.environ.get("PII_ENCRYPTION_KEY", "")
    if not raw:
        raise RuntimeError(
            "PII_ENCRYPTION_KEY is not set. "
            "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )

    try:
        _fernet = Fernet(raw.encode() if isinstance(raw, str) else raw)
    except Exception as exc:
        raise RuntimeError(f"Invalid PII_ENCRYPTION_KEY — must be a URL-safe base64 Fernet key: {exc}") from exc

    return _fernet


def encrypt_pii(plaintext: str) -> str:
    """Encrypt *plaintext* and return a URL-safe ciphertext string."""
    if not plaintext:
        return plaintext
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_pii(ciphertext: str) -> str:
    """Decrypt *ciphertext* produced by :func:`encrypt_pii`."""
    if not ciphertext:
        return ciphertext
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("PII decryption failed — ciphertext tampered or wrong key") from exc


def reset_fernet_cache() -> None:
    """Reset the cached Fernet instance — intended for tests only."""
    global _fernet
    _fernet = None


class EncryptedString(TypeDecorator):
    """Transparent Fernet encryption for SQLAlchemy String columns.

    Values are encrypted on write and decrypted on read.
    The stored column type is TEXT (unbounded String) because ciphertext
    is longer than the plaintext.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return encrypt_pii(value)

    def process_result_value(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        return decrypt_pii(value)
