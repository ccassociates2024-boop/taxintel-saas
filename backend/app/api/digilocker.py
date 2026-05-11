"""Phase 1D — DigiLocker OAuth 2.0 with PKCE.

Flow:
  1. GET  /api/v1/digilocker/auth?client_id=<UUID>  →  redirect to DigiLocker
  2. GET  /api/v1/digilocker/callback               →  exchange code for token
  3. GET  /api/v1/digilocker/documents?client_id=<UUID>  →  list linked docs
"""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
import uuid
from datetime import datetime, timedelta

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant
from app.core.config import settings
from app.core.crypto import encrypt_pii, decrypt_pii
from app.db.models import Client, DigiLockerToken, Tenant
from app.db.session import get_db

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/digilocker", tags=["digilocker"])

_DL_AUTH_URL = "https://api.digitallocker.gov.in/public/oauth2/1/authorize"
_DL_TOKEN_URL = "https://api.digitallocker.gov.in/public/oauth2/1/token"
_DL_FILES_URL = "https://api.digitallocker.gov.in/public/oauth2/1/files"

# In-memory PKCE state store (use Redis in production for multi-instance)
_pkce_store: dict[str, dict] = {}


def _available() -> bool:
    return bool(settings.digilocker_client_id and settings.digilocker_client_secret)


def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(os.urandom(40)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


@router.get("/auth")
def initiate_auth(
    client_id: uuid.UUID = Query(..., description="TaxIntel client UUID"),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Redirect the browser to DigiLocker for OAuth consent."""
    if not _available():
        raise HTTPException(status_code=503, detail="DigiLocker not configured")

    client = db.scalar(
        select(Client).where(Client.id == client_id, Client.tenant_id == tenant.id)
    )
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    state = secrets.token_urlsafe(24)
    verifier, challenge = _pkce_pair()
    _pkce_store[state] = {
        "verifier": verifier,
        "client_id": str(client_id),
        "tenant_id": str(tenant.id),
    }

    params = (
        f"?response_type=code"
        f"&client_id={settings.digilocker_client_id}"
        f"&redirect_uri={settings.digilocker_redirect_uri}"
        f"&state={state}"
        f"&code_challenge={challenge}"
        f"&code_challenge_method=S256"
    )
    return RedirectResponse(_DL_AUTH_URL + params)


@router.get("/callback")
def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    """Handle DigiLocker redirect; exchange code for tokens."""
    if not _available():
        raise HTTPException(status_code=503, detail="DigiLocker not configured")

    ctx = _pkce_store.pop(state, None)
    if not ctx:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    resp = httpx.post(
        _DL_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.digilocker_redirect_uri,
            "client_id": settings.digilocker_client_id,
            "client_secret": settings.digilocker_client_secret,
            "code_verifier": ctx["verifier"],
        },
        timeout=15,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="DigiLocker token exchange failed")

    token_data = resp.json()
    expires_in = int(token_data.get("expires_in", 3600))

    client_uuid = uuid.UUID(ctx["client_id"])
    tenant_uuid = uuid.UUID(ctx["tenant_id"])

    existing = db.scalar(select(DigiLockerToken).where(DigiLockerToken.client_id == client_uuid))
    if existing:
        existing.access_token = encrypt_pii(token_data["access_token"])
        existing.refresh_token = encrypt_pii(token_data.get("refresh_token", "")) or None
        existing.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    else:
        db.add(DigiLockerToken(
            tenant_id=tenant_uuid,
            client_id=client_uuid,
            access_token=encrypt_pii(token_data["access_token"]),
            refresh_token=encrypt_pii(token_data["refresh_token"]) if token_data.get("refresh_token") else None,
            expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
        ))
    db.commit()
    log.info("digilocker.token_stored", client_id=str(client_uuid))
    return {"status": "connected", "client_id": str(client_uuid)}


@router.get("/documents")
def list_documents(
    client_id: uuid.UUID = Query(...),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    """Fetch document list from DigiLocker for the given client."""
    token_row = db.scalar(
        select(DigiLockerToken).where(
            DigiLockerToken.client_id == client_id,
            DigiLockerToken.tenant_id == tenant.id,
        )
    )
    if not token_row:
        raise HTTPException(status_code=404, detail="Client not linked to DigiLocker")

    if datetime.utcnow() >= token_row.expires_at:
        raise HTTPException(status_code=401, detail="DigiLocker token expired — re-authenticate")

    access_token = decrypt_pii(token_row.access_token)
    resp = httpx.get(
        _DL_FILES_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="DigiLocker API error")

    return resp.json()
