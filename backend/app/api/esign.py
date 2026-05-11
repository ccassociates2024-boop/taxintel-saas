"""Phase 1C — Digio e-sign endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant
from app.db.models import Client, EsignRequest, Tenant
from app.db.session import get_db
from app.services import esign as esign_svc

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/esign", tags=["esign"])


class EsignRequestCreate(BaseModel):
    client_id: uuid.UUID
    template_type: str
    signer_email: str
    signer_name: str


class EsignRequestOut(BaseModel):
    id: uuid.UUID
    template_type: str
    status: str
    signer_email: str
    digio_document_id: str | None
    signing_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/templates")
def list_templates():
    """Return available e-sign templates."""
    return [{"key": k, **v} for k, v in esign_svc.TEMPLATES.items()]


@router.post("", response_model=EsignRequestOut)
def create_esign_request(
    payload: EsignRequestCreate,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    # Verify client belongs to this tenant
    client = db.scalar(
        select(Client).where(Client.id == payload.client_id, Client.tenant_id == tenant.id)
    )
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    result = esign_svc.create_signing_request(
        template_type=payload.template_type,
        signer_name=payload.signer_name,
        signer_email=payload.signer_email,
    )

    req = EsignRequest(
        tenant_id=tenant.id,
        client_id=payload.client_id,
        template_type=payload.template_type,
        signer_email=payload.signer_email,
        digio_document_id=result.get("document_id"),
        status=result.get("status", "pending"),
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    # Attach signing_url (not stored) for immediate use
    out = EsignRequestOut.model_validate(req)
    out.signing_url = result.get("signing_url")
    log.info("esign.request_created", id=str(req.id), template=payload.template_type)
    return out


@router.get("/{request_id}", response_model=EsignRequestOut)
def get_esign_request(
    request_id: uuid.UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    req = db.scalar(
        select(EsignRequest).where(
            EsignRequest.id == request_id, EsignRequest.tenant_id == tenant.id
        )
    )
    if not req:
        raise HTTPException(status_code=404, detail="Signing request not found")

    # Refresh status from Digio if document_id present
    if req.digio_document_id:
        try:
            fresh = esign_svc.get_document_status(req.digio_document_id)
            if fresh.get("status") != req.status:
                req.status = fresh.get("status", req.status)
                if fresh["status"] == "signed":
                    req.completed_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass  # Return cached status on network error

    return req


# ── Digio Webhook ─────────────────────────────────────────────────────────────

@router.post("/webhooks/digio")
async def digio_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    sig = request.headers.get("X-Digio-Signature", "")
    if not esign_svc.verify_webhook(body, sig):
        raise HTTPException(status_code=400, detail="Bad signature")

    import json
    event = json.loads(body)
    doc_id = event.get("document_id")
    status = event.get("status")

    if doc_id and status:
        req = db.scalar(select(EsignRequest).where(EsignRequest.digio_document_id == doc_id))
        if req:
            req.status = status
            if status == "signed":
                req.completed_at = datetime.utcnow()
            db.commit()
            log.info("esign.webhook_processed", document_id=doc_id, status=status)

    return {"status": "ok"}
