"""Provider HMAC webhook signature verification.

Every handler must call the appropriate verify_* function before executing
any business logic. If verification fails, return HTTP 400 immediately.

Usage
-----
    from app.core.webhooks import verify_razorpay, SignatureError

    @router.post("/webhooks/razorpay")
    async def razorpay_webhook(request: Request):
        body = await request.body()
        sig = request.headers.get("X-Razorpay-Signature", "")
        try:
            verify_razorpay(body, sig, settings.razorpay_webhook_secret)
        except SignatureError:
            raise HTTPException(status_code=400, detail="Invalid signature")
        ...
"""

from __future__ import annotations

import hashlib
import hmac


class SignatureError(Exception):
    """Raised when webhook HMAC verification fails."""


def _constant_compare(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


# ---------------------------------------------------------------------------
# Razorpay — HMAC-SHA256 of raw body; secret = RAZORPAY_WEBHOOK_SECRET
# ---------------------------------------------------------------------------

def verify_razorpay(body: bytes, signature: str, secret: str) -> None:
    """Verify a Razorpay webhook signature.

    Razorpay signs the raw request body with HMAC-SHA256 using the
    webhook secret configured in the Razorpay dashboard.
    """
    if not secret:
        raise SignatureError("RAZORPAY_WEBHOOK_SECRET is not configured")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not _constant_compare(expected, signature):
        raise SignatureError("Razorpay signature mismatch")


# ---------------------------------------------------------------------------
# Digio — HMAC-SHA256; header is X-Digio-Signature
# ---------------------------------------------------------------------------

def verify_digio(body: bytes, signature: str, secret: str) -> None:
    """Verify a Digio webhook signature."""
    if not secret:
        raise SignatureError("DIGIO_WEBHOOK_SECRET is not configured")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not _constant_compare(expected, signature):
        raise SignatureError("Digio signature mismatch")


# ---------------------------------------------------------------------------
# Meta (WhatsApp / Facebook) — SHA-256 HMAC; header is X-Hub-Signature-256
# The header value is prefixed with "sha256=".
# ---------------------------------------------------------------------------

def verify_meta(body: bytes, signature: str, app_secret: str) -> None:
    """Verify a Meta Cloud API webhook signature.

    The ``signature`` parameter should be the full value of the
    ``X-Hub-Signature-256`` header (``sha256=<hex>``).
    """
    if not app_secret:
        raise SignatureError("META_APP_SECRET is not configured")
    if not signature.startswith("sha256="):
        raise SignatureError("Meta signature missing 'sha256=' prefix")
    provided_hex = signature[len("sha256="):]
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    if not _constant_compare(expected, provided_hex):
        raise SignatureError("Meta signature mismatch")
