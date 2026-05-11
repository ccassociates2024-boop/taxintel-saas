from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant
from app.db.models import Tenant
from app.db.session import get_db
from app.repositories import TaxRepository
from app.schemas import DashboardOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def dashboard(tenant: Tenant = Depends(get_current_tenant), db: Session = Depends(get_db)):
    return TaxRepository(db).dashboard(tenant.id)
