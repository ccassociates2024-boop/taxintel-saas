"""Digio e-sign client — Phase 1C.

4 built-in templates:
  ENGAGEMENT_LETTER  — CA engagement letter (mandatory first-time)
  POA                — Power of Attorney for ITR filing
  FORM16_AUTH        — Form 16 collection authorisation
  MANDATE            — Auto-debit NACH mandate

All API calls are gated behind a ``_client_available()`` guard so the app
starts cleanly when DIGIO_CLIENT_ID is not set (local dev / CI).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

import httpx
import structlog

from app.core.config import settings

log = structlog.get_logger(__name__)

TEMPLATES = {
    "ENGAGEMENT_LETTER": {
        "name": "CA Engagement Letter",
        "description": "Standard engagement letter between CA firm and client as per ICAI guidelines.",
    },
    "POA": {
        "name": "Power of Attorney — ITR Filing",
        "description": "Authorises the CA firm to file income tax returns on behalf of the client.",
    },
    "FORM16_AUTH": {
        "name": "Form 16 Collection Authorisation",
        "description": "Permits the firm to collect Form 16 directly from the employer.",
    },
    "MANDATE": {
        "name": "NACH Auto-debit Mandate",
        "description": "Standing instruction for annual fee auto-debit.",
    },
}


def _auth_header() -> str:
    creds = f"{settings.digio_client_id}:{settings.digio_client_secret}"
    return "Basic " + base64.b64encode(creds.encode()).decode()


def _available() -> bool:
    return bool(settings.digio_client_id and settings.digio_client_secret)


def create_signing_request(
    template_type: str,
    signer_name: str,
    signer_email: str,
    expire_in_days: int = 7,
) -> dict[str, Any]:
    """Create a Digio signing request and return the document_id + signing_url."""
    if not _available():
        log.warning("digio.not_configured")
        return {"document_id": None, "signing_url": None, "status": "not_configured"}

    if template_type not in TEMPLATES:
        raise ValueError(f"Unknown template: {template_type}. Valid: {list(TEMPLATES)}")

    template = TEMPLATES[template_type]
    payload = {
        "signers": [{"identifier": signer_email, "name": signer_name, "sign_type": "aadhaar"}],
        "display_on_page": "first",
        "notify_signers": True,
        "send_sign_link": True,
        "expire_in_days": expire_in_days,
        "file_name": f"{template_type.lower()}.pdf",
        "title": template["name"],
        "message": template["description"],
    }

    resp = httpx.post(
        f"{settings.digio_base_url}/v2/client/document/uploadpdf",
        headers={"Authorization": _auth_header(), "Content-Type": "application/json"},
        json=payload,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    log.info("digio.request_created", document_id=data.get("id"), template=template_type)
    return {
        "document_id": data.get("id"),
        "signing_url": data.get("signing_parties", [{}])[0].get("sign_link"),
        "status": "pending",
    }


def get_document_status(document_id: str) -> dict[str, Any]:
    if not _available():
        return {"status": "not_configured"}

    resp = httpx.get(
        f"{settings.digio_base_url}/v2/client/document/{document_id}",
        headers={"Authorization": _auth_header()},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "document_id": document_id,
        "status": data.get("status", "unknown"),
        "signed_file_url": data.get("signed_file_url"),
    }


def verify_webhook(body: bytes, signature: str) -> bool:
    """Return True if the Digio webhook signature is valid."""
    if not settings.digio_webhook_secret:
        return False
    expected = hmac.new(
        settings.digio_webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
