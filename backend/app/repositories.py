from decimal import Decimal
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import (
    AisRecord,
    AuditLog,
    Client,
    Form26ASRecord,
    Recommendation,
    Tenant,
    TaxComputation,
    UploadedFile,
    User,
)
from app.schemas import ClientCreate, TenantUpdate


class TenantRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, tenant_id: UUID) -> Tenant | None:
        return self.db.get(Tenant, tenant_id)

    def create(
        self,
        legal_name: str,
        trade_name: str,
        billing_email: str,
        place_of_supply_state_code: str = "07",
    ) -> Tenant:
        tenant = Tenant(
            legal_name=legal_name,
            trade_name=trade_name,
            billing_email=billing_email.lower(),
            place_of_supply_state_code=place_of_supply_state_code,
        )
        self.db.add(tenant)
        self.db.flush()  # get tenant.id before committing
        return tenant

    def update(self, tenant: Tenant, payload: TenantUpdate) -> Tenant:
        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(tenant, field, value)
        self.db.commit()
        self.db.refresh(tenant)
        return tenant


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email.lower()))

    def create(self, email: str, password: str, full_name: str, role: str, tenant_id: UUID) -> User:
        user = User(
            email=email.lower(),
            password_hash=hash_password(password),
            full_name=full_name,
            role=role,
            tenant_id=tenant_id,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user


class ClientRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self, tenant_id: UUID) -> list[Client]:
        return list(
            self.db.scalars(
                select(Client)
                .where(Client.tenant_id == tenant_id)
                .order_by(desc(Client.created_at))
            )
        )

    def get_for_tenant(self, tenant_id: UUID, client_id: UUID) -> Client | None:
        return self.db.scalar(
            select(Client).where(Client.tenant_id == tenant_id, Client.id == client_id)
        )

    def create(self, tenant_id: UUID, owner_id: UUID, payload: ClientCreate) -> Client:
        client = Client(tenant_id=tenant_id, owner_id=owner_id, **payload.model_dump())
        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)
        return client


class TaxRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_upload(self, file: UploadedFile) -> UploadedFile:
        self.db.add(file)
        self.db.commit()
        self.db.refresh(file)
        return file

    def save_ais(self, record: AisRecord) -> AisRecord:
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def latest_ais(self, tenant_id: UUID, client_id: UUID) -> AisRecord | None:
        return self.db.scalar(
            select(AisRecord)
            .where(AisRecord.tenant_id == tenant_id, AisRecord.client_id == client_id)
            .order_by(desc(AisRecord.created_at))
        )

    def save_26as(self, record: Form26ASRecord) -> Form26ASRecord:
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def latest_26as(self, tenant_id: UUID, client_id: UUID) -> Form26ASRecord | None:
        return self.db.scalar(
            select(Form26ASRecord)
            .where(Form26ASRecord.tenant_id == tenant_id, Form26ASRecord.client_id == client_id)
            .order_by(desc(Form26ASRecord.created_at))
        )

    def save_computation(self, computation: TaxComputation) -> TaxComputation:
        self.db.add(computation)
        self.db.commit()
        self.db.refresh(computation)
        return computation

    def save_recommendations(self, items: list[Recommendation]) -> list[Recommendation]:
        self.db.add_all(items)
        self.db.commit()
        for item in items:
            self.db.refresh(item)
        return items

    def dashboard(self, tenant_id: UUID) -> dict:
        client_count = (
            self.db.scalar(select(func.count(Client.id)).where(Client.tenant_id == tenant_id)) or 0
        )
        latest_computations = list(
            self.db.scalars(
                select(TaxComputation)
                .where(TaxComputation.tenant_id == tenant_id)
                .order_by(desc(TaxComputation.created_at))
                .limit(50)
            )
        )
        recommendations = list(
            self.db.scalars(
                select(Recommendation)
                .where(Recommendation.tenant_id == tenant_id)
                .order_by(desc(Recommendation.created_at))
                .limit(5)
            )
        )
        mismatches = (
            self.db.scalar(
                select(func.count(Form26ASRecord.id)).where(
                    Form26ASRecord.tenant_id == tenant_id,
                    Form26ASRecord.mismatch_amount != 0,
                )
            ) or 0
        )
        tax_payable = sum((item.tax_payable for item in latest_computations), Decimal("0"))
        refunds = sum((item.refund_estimate for item in latest_computations), Decimal("0"))
        avg_health = int(
            sum((item.health_score for item in latest_computations), 0)
            / max(len(latest_computations), 1)
        )
        return {
            "client_count": client_count,
            "tax_payable": tax_payable,
            "refund_estimate": refunds,
            "average_health_score": avg_health,
            "ais_mismatch_count": mismatches,
            "recent_recommendations": recommendations,
        }


def audit(
    db: Session,
    owner_id: UUID | None,
    action: str,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict | None = None,
    tenant_id: UUID | None = None,
) -> None:
    db.add(
        AuditLog(
            tenant_id=tenant_id,
            owner_id=owner_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=metadata or {},
        )
    )
    db.commit()
