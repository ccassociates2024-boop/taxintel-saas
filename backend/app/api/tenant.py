from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant
from app.db.models import Tenant
from app.db.session import get_db
from app.repositories import TenantRepository
from app.schemas import TenantOut, TenantUpdate

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.get("", response_model=TenantOut)
def get_tenant(tenant: Tenant = Depends(get_current_tenant)):
    return tenant


@router.patch("", response_model=TenantOut)
def update_tenant(
    payload: TenantUpdate,
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    return TenantRepository(db).update(tenant, payload)
