from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_current_tenant
from app.db.models import Tenant, TaxComputation, User
from app.db.session import get_db
from app.repositories import ClientRepository, TaxRepository, audit
from app.schemas import ComputeRequest, TaxComputationOut
from app.services.tax_engine import compute_tax

router = APIRouter(prefix="/tax", tags=["tax"])


@router.post("/{client_id}/compute", response_model=TaxComputationOut)
def compute(
    client_id: UUID,
    payload: ComputeRequest,
    user: User = Depends(current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    if not ClientRepository(db).get_for_tenant(tenant.id, client_id):
        raise HTTPException(status_code=404, detail="Client not found")
    result = compute_tax(payload)
    saved = TaxRepository(db).save_computation(
        TaxComputation(
            tenant_id=tenant.id,
            owner_id=user.id,
            client_id=client_id,
            assessment_year=result.assessment_year,
            old_regime_tax=result.old_regime_tax,
            new_regime_tax=result.new_regime_tax,
            recommended_regime=result.recommended_regime,
            tax_payable=result.tax_payable,
            refund_estimate=result.refund_estimate,
            health_score=result.health_score,
            computation_json=result.computation_json,
        )
    )
    audit(db, user.id, "TAX_COMPUTED", "client", str(client_id), result.model_dump(mode="json"), tenant_id=tenant.id)
    return TaxComputationOut.model_validate(saved)
