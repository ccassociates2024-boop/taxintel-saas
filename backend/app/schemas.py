from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str
    role: str

    model_config = {"from_attributes": True}


class AuthRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class RegisterRequest(AuthRequest):
    full_name: str
    role: str = "CA"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class TenantOut(BaseModel):
    id: UUID
    legal_name: str
    trade_name: str
    gstin: str | None = None
    billing_email: EmailStr
    place_of_supply_state_code: str
    plan: str
    is_active: bool

    model_config = {"from_attributes": True}


class TenantUpdate(BaseModel):
    legal_name: str | None = None
    trade_name: str | None = None
    gstin: str | None = None
    billing_email: EmailStr | None = None
    place_of_supply_state_code: str | None = None


class ClientCreate(BaseModel):
    full_name: str
    pan: str = Field(min_length=10, max_length=10)
    email: EmailStr | None = None
    phone: str | None = None
    residential_status: str = "RESIDENT"
    client_type: str = "INDIVIDUAL"


class ClientOut(ClientCreate):
    id: UUID

    model_config = {"from_attributes": True}


class AisSummary(BaseModel):
    salary: Decimal = Decimal("0")
    interest_income: Decimal = Decimal("0")
    dividend_income: Decimal = Decimal("0")
    capital_gains: Decimal = Decimal("0")
    tds_tcs: Decimal = Decimal("0")
    foreign_remittance: Decimal = Decimal("0")
    high_value_transactions: Decimal = Decimal("0")


class Form26ASSummary(BaseModel):
    salary_tds: Decimal = Decimal("0")
    non_salary_tds: Decimal = Decimal("0")
    tcs: Decimal = Decimal("0")
    advance_tax_paid: Decimal = Decimal("0")
    mismatch_amount: Decimal = Decimal("0")


class ComputeRequest(BaseModel):
    assessment_year: str = "2026-27"
    salary: Decimal = Decimal("0")
    business_income: Decimal = Decimal("0")
    house_property_income: Decimal = Decimal("0")
    capital_gains: Decimal = Decimal("0")
    deductions: Decimal = Decimal("0")
    tax_credits: Decimal = Decimal("0")
    filing_delay_months: int = 0
    advance_tax_shortfall: Decimal = Decimal("0")


class TaxComputationOut(BaseModel):
    id: UUID | None = None
    assessment_year: str
    old_regime_tax: Decimal
    new_regime_tax: Decimal
    recommended_regime: str
    tax_payable: Decimal
    refund_estimate: Decimal
    health_score: int
    computation_json: dict = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class RecommendationOut(BaseModel):
    id: UUID | None = None
    title: str
    category: str
    priority: str
    estimated_savings: Decimal
    summary: str
    payload: dict = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class DashboardOut(BaseModel):
    client_count: int
    tax_payable: Decimal
    refund_estimate: Decimal
    average_health_score: int
    ais_mismatch_count: int
    recent_recommendations: list[RecommendationOut]
