import hashlib
from pathlib import Path
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_current_tenant
from app.core import storage
from app.core.config import settings
from app.db.models import AisRecord, Form26ASRecord, Tenant, UploadedFile, User
from app.db.session import get_db
from app.repositories import ClientRepository, TaxRepository, audit
from app.schemas import AisSummary, Form26ASSummary
from app.services.parsers import parse_26as, parse_ais

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/uploads", tags=["uploads"])

ALLOWED_EXTENSIONS = {".pdf", ".json", ".xlsx", ".xlsm", ".xls"}
_CONTENT_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".json": "application/json",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xlsm": "application/vnd.ms-excel.sheet.macroEnabled.12",
    ".xls": "application/vnd.ms-excel",
}


@router.post("/ais", response_model=AisSummary)
async def upload_ais(
    client_id: UUID = Form(...),
    assessment_year: str = Form("2026-27"),
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    content, stored = await _store_upload(db, user, tenant, client_id, "AIS", file)
    summary = parse_ais(content, stored.original_name)
    record = AisRecord(
        tenant_id=tenant.id,
        owner_id=user.id,
        client_id=client_id,
        uploaded_file_id=stored.id,
        assessment_year=assessment_year,
        raw_json=summary.model_dump(mode="json"),
        **summary.model_dump(),
    )
    TaxRepository(db).save_ais(record)
    audit(db, user.id, "AIS_UPLOADED", "client", str(client_id), summary.model_dump(mode="json"), tenant_id=tenant.id)
    log.info("ais.uploaded", client_id=str(client_id), assessment_year=assessment_year)
    return summary


@router.post("/26as", response_model=Form26ASSummary)
async def upload_26as(
    client_id: UUID = Form(...),
    assessment_year: str = Form("2026-27"),
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    content, stored = await _store_upload(db, user, tenant, client_id, "26AS", file)
    repo = TaxRepository(db)
    ais = repo.latest_ais(tenant.id, client_id)
    ais_summary = AisSummary(**ais.raw_json) if ais else None
    summary = parse_26as(content, stored.original_name, ais_summary)
    record = Form26ASRecord(
        tenant_id=tenant.id,
        owner_id=user.id,
        client_id=client_id,
        uploaded_file_id=stored.id,
        assessment_year=assessment_year,
        raw_json=summary.model_dump(mode="json"),
        **summary.model_dump(),
    )
    repo.save_26as(record)
    audit(db, user.id, "FORM26AS_UPLOADED", "client", str(client_id), summary.model_dump(mode="json"), tenant_id=tenant.id)
    log.info("form26as.uploaded", client_id=str(client_id), assessment_year=assessment_year)
    return summary


async def _store_upload(
    db: Session,
    user: User,
    tenant: Tenant,
    client_id: UUID,
    file_type: str,
    file: UploadFile,
) -> tuple[bytes, UploadedFile]:
    if not ClientRepository(db).get_for_tenant(tenant.id, client_id):
        raise HTTPException(status_code=404, detail="Client not found")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Unsupported file type")

    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")

    digest = hashlib.sha256(content).hexdigest()
    s3_key = f"tenants/{tenant.id}/clients/{client_id}/{digest}{ext}"
    content_type = _CONTENT_TYPES.get(ext, file.content_type or "application/octet-stream")

    await storage.async_put_bytes(s3_key, content, content_type)

    uploaded = TaxRepository(db).save_upload(
        UploadedFile(
            tenant_id=tenant.id,
            owner_id=user.id,
            client_id=client_id,
            file_type=file_type,
            original_name=file.filename or f"upload{ext}",
            storage_path=s3_key,
            mime_type=content_type,
            file_hash=digest,
            status="PROCESSED",
        )
    )
    return content, uploaded
