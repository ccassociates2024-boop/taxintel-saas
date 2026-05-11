"""Shared pytest fixtures for the backend test suite."""

from __future__ import annotations

import os

import pytest
from cryptography.fernet import Fernet

# Set required env vars before any app import
_TEST_FERNET_KEY = Fernet.generate_key().decode()
os.environ.setdefault("PII_ENCRYPTION_KEY", _TEST_FERNET_KEY)
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret-for-pytest-only")
os.environ.setdefault("S3_BUCKET", "test-bucket")
os.environ.setdefault("S3_ACCESS_KEY", "test")
os.environ.setdefault("S3_SECRET_KEY", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")


@pytest.fixture(autouse=True)
def reset_crypto_cache():
    """Ensure each test starts with a fresh Fernet instance."""
    from app.core.crypto import reset_fernet_cache
    reset_fernet_cache()
    yield
    reset_fernet_cache()
