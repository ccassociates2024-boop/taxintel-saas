"""Meta Cloud API — WhatsApp Business messaging — Phase 1E.

Template messages only (approved by Meta before sending).
Built-in templates:
  tax_reminder   — ITR filing deadline reminder
  ais_alert      — AIS mismatch detected
  doc_request    — Request client to upload document
  invoice_ready  — Invoice available for download
"""
from __future__ import annotations

import hashlib
import hmac
from typing import Any

import httpx
import structlog

from app.core.config import settings

log = structlog.get_logger(__name__)

_GRAPH_URL = "https://graph.facebook.com/v19.0"

# WhatsApp template names as approved in Meta Business Manager
TEMPLATES = {
    "tax_reminder": "itr_filing_reminder",
    "ais_alert": "ais_mismatch_alert",
    "doc_request": "document_upload_request",
    "invoice_ready": "invoice_ready_notification",
}


def _available() -> bool:
    return bool(settings.meta_whatsapp_token and settings.meta_phone_number_id)


def send_template_message(
    to_phone: str,
    template_key: str,
    params: list[str] | None = None,
    language: str = "en",
) -> dict[str, Any]:
    """Send a pre-approved template message.

    Args:
        to_phone:     Recipient phone in E.164 format (e.g. +919876543210).
        template_key: One of TEMPLATES keys.
        params:       Ordered list of body-variable substitutions.
        language:     BCP-47 language code (default "en").
    """
    if not _available():
        log.warning("whatsapp.not_configured")
        return {"status": "not_configured"}

    template_name = TEMPLATES.get(template_key, template_key)
    components: list[dict] = []
    if params:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": p} for p in params],
        })

    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
            "components": components,
        },
    }

    resp = httpx.post(
        f"{_GRAPH_URL}/{settings.meta_phone_number_id}/messages",
        headers={
            "Authorization": f"Bearer {settings.meta_whatsapp_token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    msg_id = data.get("messages", [{}])[0].get("id")
    log.info("whatsapp.sent", to=to_phone, template=template_name, message_id=msg_id)
    return {"status": "sent", "message_id": msg_id}


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Validate Meta webhook X-Hub-Signature-256 header."""
    if not settings.meta_app_secret:
        return False
    if not signature.startswith("sha256="):
        return False
    expected = hmac.new(settings.meta_app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature[len("sha256="):])
