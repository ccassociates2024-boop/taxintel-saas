"""Phase 1E — WhatsApp via Meta Cloud API."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.api.deps import get_current_tenant
from app.core.config import settings
from app.db.models import Tenant
from app.services import whatsapp as wa

log = structlog.get_logger(__name__)
router = APIRouter(tags=["whatsapp"])


class SendMessageRequest(BaseModel):
    to_phone: str
    template_key: str
    params: list[str] = []


@router.post("/whatsapp/send")
def send_whatsapp(
    payload: SendMessageRequest,
    tenant: Tenant = Depends(get_current_tenant),
):
    """Send a template WhatsApp message."""
    try:
        result = wa.send_template_message(
            to_phone=payload.to_phone,
            template_key=payload.template_key,
            params=payload.params or None,
        )
    except Exception as exc:
        log.error("whatsapp.send_failed", error=str(exc))
        raise HTTPException(status_code=502, detail=f"WhatsApp delivery failed: {exc}")
    return result


@router.get("/webhooks/whatsapp")
def verify_whatsapp_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    """Meta webhook verification handshake."""
    if hub_mode == "subscribe" and hub_verify_token == (settings.meta_verify_token or ""):
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/webhooks/whatsapp")
async def receive_whatsapp_webhook(request: Request):
    """Receive incoming WhatsApp messages / status updates."""
    body = await request.body()
    sig = request.headers.get("X-Hub-Signature-256", "")
    if not wa.verify_webhook_signature(body, sig):
        log.warning("whatsapp.bad_signature")
        raise HTTPException(status_code=400, detail="Bad signature")

    import json
    event = json.loads(body)
    # Future: route inbound messages to client records
    log.info("whatsapp.webhook_received", entry_count=len(event.get("entry", [])))
    return {"status": "ok"}
