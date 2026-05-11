"""Unit tests for backend/app/core/webhooks.py."""

from __future__ import annotations

import hashlib
import hmac

import pytest

from app.core.webhooks import SignatureError, verify_digio, verify_meta, verify_razorpay


def _make_razorpay_sig(body: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _make_meta_sig(body: bytes, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# Razorpay
# ---------------------------------------------------------------------------

class TestVerifyRazorpay:
    def test_valid_signature(self):
        body = b'{"event": "subscription.charged"}'
        secret = "webhook-secret-razorpay"
        sig = _make_razorpay_sig(body, secret)
        verify_razorpay(body, sig, secret)  # must not raise

    def test_tampered_body_fails(self):
        body = b'{"event": "subscription.charged"}'
        secret = "webhook-secret-razorpay"
        sig = _make_razorpay_sig(body, secret)
        with pytest.raises(SignatureError, match="mismatch"):
            verify_razorpay(b'{"event": "tampered"}', sig, secret)

    def test_wrong_secret_fails(self):
        body = b'{"event": "payment.failed"}'
        sig = _make_razorpay_sig(body, "correct-secret")
        with pytest.raises(SignatureError, match="mismatch"):
            verify_razorpay(body, sig, "wrong-secret")

    def test_empty_secret_fails(self):
        with pytest.raises(SignatureError, match="not configured"):
            verify_razorpay(b"body", "sig", "")

    def test_empty_signature_fails(self):
        with pytest.raises(SignatureError, match="mismatch"):
            verify_razorpay(b"body", "", "secret")


# ---------------------------------------------------------------------------
# Digio
# ---------------------------------------------------------------------------

class TestVerifyDigio:
    def test_valid_signature(self):
        body = b'{"event": "sign.success"}'
        secret = "digio-webhook-secret"
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        verify_digio(body, sig, secret)  # must not raise

    def test_tampered_body_fails(self):
        body = b'{"event": "sign.success"}'
        secret = "digio-webhook-secret"
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        with pytest.raises(SignatureError, match="mismatch"):
            verify_digio(b'{"event": "tampered"}', sig, secret)

    def test_empty_secret_fails(self):
        with pytest.raises(SignatureError, match="not configured"):
            verify_digio(b"body", "sig", "")


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------

class TestVerifyMeta:
    def test_valid_signature(self):
        body = b'{"object": "whatsapp_business_account"}'
        secret = "meta-app-secret"
        sig = _make_meta_sig(body, secret)
        verify_meta(body, sig, secret)  # must not raise

    def test_missing_prefix_fails(self):
        body = b'{"object": "test"}'
        secret = "meta-app-secret"
        raw_hex = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        with pytest.raises(SignatureError, match="sha256="):
            verify_meta(body, raw_hex, secret)  # no "sha256=" prefix

    def test_tampered_body_fails(self):
        body = b'{"object": "test"}'
        secret = "meta-app-secret"
        sig = _make_meta_sig(body, secret)
        with pytest.raises(SignatureError, match="mismatch"):
            verify_meta(b'{"object": "injected"}', sig, secret)

    def test_wrong_secret_fails(self):
        body = b'{"object": "test"}'
        sig = _make_meta_sig(body, "correct-secret")
        with pytest.raises(SignatureError, match="mismatch"):
            verify_meta(body, sig, "wrong-secret")

    def test_empty_secret_fails(self):
        with pytest.raises(SignatureError, match="not configured"):
            verify_meta(b"body", "sha256=abc", "")
