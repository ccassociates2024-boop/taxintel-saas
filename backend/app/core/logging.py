"""Structured JSON logging via structlog with a PII redactor processor.

Call configure_logging() once at application startup (in main.py).
All application code should then import structlog and use:

    import structlog
    log = structlog.get_logger(__name__)
    log.info("client.created", client_id=str(client.id))

PII fields that are redacted in every log event
------------------------------------------------
- Values in keys that match PII_KEY_PATTERNS (pan, aadhaar, token, otp, …)
- Strings that match PAN pattern (5 letters + 4 digits + 1 letter)
- 12-digit Aadhaar numbers embedded in string values
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

import structlog

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

_PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
_AADHAAR_RE = re.compile(r"\b[2-9]\d{11}\b")  # 12-digit starting 2-9

_PII_KEY_PATTERNS: tuple[str, ...] = (
    "pan",
    "aadhaar",
    "access_token",
    "refresh_token",
    "token",
    "otp",
    "pin",
    "secret",
    "password",
    "password_hash",
)

_REDACTED = "[REDACTED]"


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        value = _PAN_RE.sub(_REDACTED, value)
        value = _AADHAAR_RE.sub(_REDACTED, value)
    return value


def _redact_dict(d: dict) -> dict:
    out: dict = {}
    for k, v in d.items():
        lower_key = k.lower()
        if any(pat in lower_key for pat in _PII_KEY_PATTERNS):
            out[k] = _REDACTED
        elif isinstance(v, dict):
            out[k] = _redact_dict(v)
        elif isinstance(v, list):
            out[k] = [_redact_value(item) if not isinstance(item, dict) else _redact_dict(item) for item in v]
        else:
            out[k] = _redact_value(v)
    return out


def pii_redactor(logger, method: str, event_dict: dict) -> dict:
    """structlog processor that redacts PII from every log event."""
    return _redact_dict(event_dict)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def configure_logging(log_level: str = "INFO", json_logs: bool = True) -> None:
    """Configure structlog for the application.

    Call this exactly once at startup before any log messages are emitted.
    """
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        pii_redactor,
    ]

    if json_logs:
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(log_level.upper())),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level.upper())

    # Quiet noisy libraries
    for lib in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(lib).setLevel(logging.WARNING)
