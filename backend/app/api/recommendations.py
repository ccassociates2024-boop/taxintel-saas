from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_user, get_current_tenant
from app.db.models import Recommendation, Tenant, User
from app.db.session import get_db
from app.repositories import ClientRepository, TaxRepository, audit
from app.schemas import ComputeRequest, RecommendationOut
from app.services.recommendations import generate_recommendations
from app.services.tax_engine import compute_tax

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/{client_id}/generate", response_model=list[RecommendationOut])
def generate(
    client_id: UUID,
    payload: ComputeRequest,
    user: User = Depends(current_user),
    tenant: Tenant = Depends(get_current_tenant),
    db: Session = Depends(get_db),
):
    if not ClientRepository(db).get_for_tenant(tenant.id, client_id):
        raise HTTPException(status_code=404, detail="Client not found")
    repo = TaxRepository(db)
    computation = compute_tax(payload)
    recs = generate_recommendations(
        repo.latest_ais(tenant.id, client_id),
        repo.latest_26as(tenant.id, client_id),
        computation,
    )
    saved = repo.save_recommendations(
        [
            Recommendation(
                tenant_id=tenant.id,
                owner_id=user.id,
                client_id=client_id,
                assessment_year=payload.assessment_year,
                title=item.title,
                category=item.category,
                priority=item.priority,
                estimated_savings=item.estimated_savings,
                summary=item.summary,
                payload=item.payload,
            )
            for item in recs
        ]
    )
    audit(db, user.id, "RECOMMENDATIONS_GENERATED", "client", str(client_id), {"count": len(saved)}, tenant_id=tenant.id)
    return saved
