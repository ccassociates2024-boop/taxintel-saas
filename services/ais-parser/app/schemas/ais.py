from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class DeclaredTaxData(BaseModel):
    salary: Decimal = Decimal("0")
    interest_income: Decimal = Decimal("0")
    capital_gains: Decimal = Decimal("0")
    dividend_income: Decimal = Decimal("0")
    tds_tcs: Decimal = Decimal("0")
    foreign_remittance: Decimal = Decimal("0")
    high_value_transactions: Decimal = Decimal("0")


class AisTransactionOut(BaseModel):
    category: str
    amount: Decimal
    transaction_date: date | None = None
    source_name: str | None = None
    information_code: str | None = None
    confidence: Decimal = Field(ge=0, le=1)
    raw: dict = Field(default_factory=dict)


class AisSummary(BaseModel):
    salary: Decimal = Decimal("0")
    interest_income: Decimal = Decimal("0")
    capital_gains: Decimal = Decimal("0")
    dividend_income: Decimal = Decimal("0")
    tds_tcs: Decimal = Decimal("0")
    foreign_remittance: Decimal = Decimal("0")
    high_value_transactions: Decimal = Decimal("0")


class AisParseResult(BaseModel):
    assessment_year: str
    parser_version: str = "1.0.0"
    summary: AisSummary
    transactions: list[AisTransactionOut]
    warnings: list[str] = Field(default_factory=list)
    raw_payload: dict = Field(default_factory=dict)


class MismatchFinding(BaseModel):
    category: str
    severity: str
    ais_amount: Decimal
    declared_amount: Decimal
    difference: Decimal
    message: str
    evidence: dict = Field(default_factory=dict)


class MismatchRequest(BaseModel):
    ais_result: AisParseResult
    declared: DeclaredTaxData
    absolute_tolerance: Decimal = Decimal("100")
    percentage_tolerance: Decimal = Decimal("0.01")


class MismatchResponse(BaseModel):
    findings: list[MismatchFinding]


class StoredParseResponse(BaseModel):
    import_id: UUID
    result: AisParseResult
    mismatches: list[MismatchFinding]

