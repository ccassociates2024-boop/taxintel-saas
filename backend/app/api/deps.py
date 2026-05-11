from uuid import UUID

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.models import Tenant, User
from app.db.session import get_db


def current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    payload = _require_payload(authorization)
    user = db.get(User, UUID(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Inactive user")
    return user


def get_current_tenant(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Tenant:
    payload = _require_payload(authorization)
    tenant_id = payload.get("tid")
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Token missing tenant claim")
    tenant = db.get(Tenant, UUID(tenant_id))
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=401, detail="Tenant not found or inactive")
    return tenant


def _require_payload(authorization: str | None) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    payload = decode_token(authorization.split(" ", 1)[1])
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload
