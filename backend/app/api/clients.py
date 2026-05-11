from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_current_tenant
from app.db.models import Tenant, User
from app.db.session import get_db
from app.repositories import ClientRepository, audit
from app.schemas import ClientCreate, ClientOut

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientOut])
def list_clients(
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return ClientRepository(db).list(tenant.id)


@router.post("", response_model=ClientOut)
def create_client(
    payload: ClientCreate,
    user: User = Depends(current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    client = ClientRepository(db).create(tenant.id, user.id, payload)
    audit(db, user.id, "CLIENT_CREATED", "client", str(client.id), tenant_id=tenant.id)
    return client


@router.get("/{client_id}", response_model=ClientOut)
def get_client(
    client_id: UUID,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    client = ClientRepository(db).get_for_tenant(tenant.id, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client
