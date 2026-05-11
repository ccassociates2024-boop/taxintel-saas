"""Unit tests for backend/app/core/crypto.py."""

from __future__ import annotations

import os

import pytest
from cryptography.fernet import Fernet


def _set_key(key: str) -> None:
    from app.core.crypto import reset_fernet_cache
    reset_fernet_cache()
    os.environ["PII_ENCRYPTION_KEY"] = key


# ---------------------------------------------------------------------------
# encrypt_pii / decrypt_pii
# ---------------------------------------------------------------------------

class TestEncryptDecrypt:
    def test_roundtrip(self):
        from app.core.crypto import decrypt_pii, encrypt_pii

        plaintext = "ABCDE1234F"
        ct = encrypt_pii(plaintext)
        assert ct != plaintext
        assert decrypt_pii(ct) == plaintext

    def test_empty_string_passthrough(self):
        from app.core.crypto import decrypt_pii, encrypt_pii

        assert encrypt_pii("") == ""
        assert decrypt_pii("") == ""

    def test_none_passthrough_via_type_decorator(self):
        """None values should survive the TypeDecorator without error."""
        from app.core.crypto import EncryptedString

        td = EncryptedString()
        assert td.process_bind_param(None, None) is None
        assert td.process_result_value(None, None) is None

    def test_different_keys_fail_decryption(self):
        from app.core.crypto import decrypt_pii, encrypt_pii

        ct = encrypt_pii("secret data")

        # Encrypt was done with the conftest key; try decrypting with a different key
        original = os.environ.get("PII_ENCRYPTION_KEY", "")
        try:
            _set_key(Fernet.generate_key().decode())
            with pytest.raises(ValueError, match="decryption failed"):
                decrypt_pii(ct)
        finally:
            _set_key(original)

    def test_missing_key_raises_runtime_error(self):
        from app.core.crypto import encrypt_pii, reset_fernet_cache

        reset_fernet_cache()
        old = os.environ.pop("PII_ENCRYPTION_KEY", None)
        try:
            with pytest.raises(RuntimeError, match="PII_ENCRYPTION_KEY"):
                encrypt_pii("data")
        finally:
            if old:
                os.environ["PII_ENCRYPTION_KEY"] = old
            reset_fernet_cache()

    def test_invalid_key_raises_runtime_error(self):
        original = os.environ.get("PII_ENCRYPTION_KEY", "")
        try:
            _set_key("not-a-valid-fernet-key")
            from app.core.crypto import encrypt_pii

            with pytest.raises(RuntimeError, match="Invalid PII_ENCRYPTION_KEY"):
                encrypt_pii("data")
        finally:
            _set_key(original)

    def test_ciphertext_is_not_plaintext(self):
        from app.core.crypto import encrypt_pii

        pan = "ABCPQ1234R"
        ct = encrypt_pii(pan)
        assert pan not in ct

    def test_phone_number_roundtrip(self):
        from app.core.crypto import decrypt_pii, encrypt_pii

        phone = "+919876543210"
        assert decrypt_pii(encrypt_pii(phone)) == phone

    def test_email_roundtrip(self):
        from app.core.crypto import decrypt_pii, encrypt_pii

        email = "taxpayer@example.com"
        assert decrypt_pii(encrypt_pii(email)) == email


# ---------------------------------------------------------------------------
# EncryptedString SQLAlchemy TypeDecorator
# ---------------------------------------------------------------------------

class TestEncryptedStringTypeDecorator:
    def test_bind_param_encrypts(self):
        from app.core.crypto import EncryptedString, decrypt_pii

        td = EncryptedString()
        stored = td.process_bind_param("ZYXWV5432A", None)
        assert stored is not None
        assert stored != "ZYXWV5432A"
        assert decrypt_pii(stored) == "ZYXWV5432A"

    def test_result_value_decrypts(self):
        from app.core.crypto import EncryptedString, encrypt_pii

        td = EncryptedString()
        ct = encrypt_pii("ZYXWV5432A")
        assert td.process_result_value(ct, None) == "ZYXWV5432A"

    def test_bind_none_returns_none(self):
        from app.core.crypto import EncryptedString

        td = EncryptedString()
        assert td.process_bind_param(None, None) is None

    def test_result_none_returns_none(self):
        from app.core.crypto import EncryptedString

        td = EncryptedString()
        assert td.process_result_value(None, None) is None
