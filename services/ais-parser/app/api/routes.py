from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.db.repository import AisRepository
from app.db.session import get_db
from app.schemas.ais import DeclaredTaxData, MismatchRequest, MismatchResponse, StoredParseResponse
from app.services.mismatch import detect_mismatches
from app.services.parser import AisParserService

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/ais/parse")
async def parse_ais(
    assessment_year: str = Form(...),
    file: UploadFile = File(...),
):
    result, _ = await AisParserService().parse_upload(file, assessment_year)
    return result


@router.post("/ais/parse-and-store", response_model=StoredParseResponse)
async def parse_and_store_ais(
    tenant_id: UUID = Form(...),
    client_id: UUID = Form(...),
    assessment_year: str = Form(...),
    declared_salary: Decimal = Form(Decimal("0")),
    declared_interest_income: Decimal = Form(Decimal("0")),
    declared_capital_gains: Decimal = Form(Decimal("0")),
    declared_dividend_income: Decimal = Form(Decimal("0")),
    declared_tds_tcs: Decimal = Form(Decimal("0")),
    declared_foreign_remittance: Decimal = Form(Decimal("0")),
    declared_high_value_transactions: Decimal = Form(Decimal("0")),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    result, file_hash = await AisParserService().parse_upload(file, assessment_year)
    declared = DeclaredTaxData(
        salary=declared_salary,
        interest_income=declared_interest_income,
        capital_gains=declared_capital_gains,
        dividend_income=declared_dividend_income,
        tds_tcs=declared_tds_tcs,
        foreign_remittance=declared_foreign_remittance,
        high_value_transactions=declared_high_value_transactions,
    )
    mismatches = detect_mismatches(result, declared)
    ais_import = AisRepository(db).save_import(
        tenant_id=tenant_id,
        client_id=client_id,
        file_name=file.filename or "ais-upload",
        file_hash=file_hash,
        result=result,
        mismatches=mismatches,
    )
    return StoredParseResponse(import_id=ais_import.id, result=result, mismatches=mismatches)


@router.post("/ais/mismatches", response_model=MismatchResponse)
def mismatches(request: MismatchRequest):
    return MismatchResponse(
        findings=detect_mismatches(
            request.ais_result,
            request.declared,
            absolute_tolerance=request.absolute_tolerance,
            percentage_tolerance=request.percentage_tolerance,
        )
    )

