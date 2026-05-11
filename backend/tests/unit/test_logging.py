"""Unit tests for backend/app/core/logging.py PII redactor."""

from __future__ import annotations

import pytest

from app.core.logging import pii_redactor


class TestPiiRedactor:
    def _redact(self, event_dict: dict) -> dict:
        return pii_redactor(None, "info", event_dict)

    # PAN pattern redaction
    def test_pan_in_string_value_is_redacted(self):
        result = self._redact({"message": "Client PAN is ABCDE1234F today"})
        assert "ABCDE1234F" not in result["message"]
        assert "[REDACTED]" in result["message"]

    def test_pan_in_pan_key_is_redacted(self):
        result = self._redact({"pan": "ABCDE1234F"})
        assert result["pan"] == "[REDACTED]"

    # Aadhaar pattern redaction
    def test_aadhaar_in_string_is_redacted(self):
        result = self._redact({"info": "Aadhaar: 234567890123"})
        assert "234567890123" not in result["info"]

    # Key-name-based redaction
    def test_access_token_key_is_redacted(self):
        result = self._redact({"access_token": "eyJhbGciOiJSUzI1NiJ9..."})
        assert result["access_token"] == "[REDACTED]"

    def test_refresh_token_key_is_redacted(self):
        result = self._redact({"refresh_token": "abc123"})
        assert result["refresh_token"] == "[REDACTED]"

    def test_otp_key_is_redacted(self):
        result = self._redact({"otp": "123456"})
        assert result["otp"] == "[REDACTED]"

    def test_password_hash_key_is_redacted(self):
        result = self._redact({"password_hash": "$2b$12$..."})
        assert result["password_hash"] == "[REDACTED]"

    # Safe values pass through
    def test_non_pii_value_passes_through(self):
        result = self._redact({"client_id": "some-uuid", "amount": 9999})
        assert result["client_id"] == "some-uuid"
        assert result["amount"] == 9999

    # Nested dict redaction
    def test_nested_dict_pii_is_redacted(self):
        result = self._redact({"user": {"pan": "XYZAB5678C", "name": "Test"}})
        assert result["user"]["pan"] == "[REDACTED]"
        assert result["user"]["name"] == "Test"

    # List values
    def test_list_with_pan_strings_redacted(self):
        result = self._redact({"items": ["ABCDE1234F", "normal"]})
        assert "[REDACTED]" in result["items"][0]
        assert result["items"][1] == "normal"

    def test_event_key_passes_through(self):
        result = self._redact({"event": "client.created", "tenant_id": "abc"})
        assert result["event"] == "client.created"


# ---------------------------------------------------------------------------
# configure_logging()
# ---------------------------------------------------------------------------

class TestConfigureLogging:
    def test_configure_does_not_raise(self):
        from app.core.logging import configure_logging
        configure_logging(log_level="WARNING", json_logs=False)

    def test_configure_json_mode(self):
        from app.core.logging import configure_logging
        configure_logging(log_level="INFO", json_logs=True)

    def test_structlog_usable_after_configure(self):
        import structlog
        from app.core.logging import configure_logging

        configure_logging(log_level="INFO", json_logs=False)
        log = structlog.get_logger("test")
        log.info("test.event", key="value")  # must not raise
