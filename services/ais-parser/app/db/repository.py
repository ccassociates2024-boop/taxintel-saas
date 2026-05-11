from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import AisImport, AisMismatch, AisTransaction
from app.schemas.ais import AisParseResult, MismatchFinding


class AisRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_import(
        self,
        *,
        tenant_id: UUID,
        client_id: UUID,
        file_name: str,
        file_hash: str,
        result: AisParseResult,
        mismatches: list[MismatchFinding],
    ) -> AisImport:
        ais_import = AisImport(
            tenant_id=tenant_id,
            client_id=client_id,
            assessment_year=result.assessment_year,
            source_file_name=file_name,
            source_file_hash=file_hash,
            parser_version=result.parser_version,
            raw_payload=result.raw_payload,
        )

        for txn in result.transactions:
            ais_import.transactions.append(
                AisTransaction(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    assessment_year=result.assessment_year,
                    category=txn.category,
                    information_code=txn.information_code,
                    source_name=txn.source_name,
                    amount=Decimal(str(txn.amount)),
                    transaction_date=txn.transaction_date,
                    confidence=Decimal(str(txn.confidence)),
                    raw_json=txn.raw,
                )
            )

        for item in mismatches:
            ais_import.mismatches.append(
                AisMismatch(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    assessment_year=result.assessment_year,
                    category=item.category,
                    severity=item.severity,
                    ais_amount=Decimal(str(item.ais_amount)),
                    declared_amount=Decimal(str(item.declared_amount)),
                    difference=Decimal(str(item.difference)),
                    message=item.message,
                    evidence_json=item.evidence,
                )
            )

        self.db.add(ais_import)
        self.db.commit()
        self.db.refresh(ais_import)
        return ais_import

