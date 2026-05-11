from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]
Regime = Literal["OLD", "NEW"]


class AisData(BaseModel):
    salary: Decimal = Decimal("0")
    interest_income: Decimal = Decimal("0")
    dividend_income: Decimal = Decimal("0")
    capital_gains: Decimal = Decimal("0")
    business_income: Decimal = Decimal("0")
    tds_tcs: Decimal = Decimal("0")
    foreign_remittance: Decimal = Decimal("0")
    high_value_transactions: Decimal = Decimal("0")


class Form26ASData(BaseModel):
    salary_tds: Decimal = Decimal("0")
    non_salary_tds: Decimal = Decimal("0")
    tcs: Decimal = Decimal("0")
    advance_tax_paid: Decimal = Decimal("0")
    self_assessment_tax_paid: Decimal = Decimal("0")


class SalaryInput(BaseModel):
    gross_salary: Decimal = Decimal("0")
    standard_deduction: Decimal = Decimal("50000")
    hra_exemption: Decimal = Decimal("0")
    professional_tax: Decimal = Decimal("0")


class CapitalGainsInput(BaseModel):
    stcg_equity_111a: Decimal = Decimal("0")
    ltcg_equity_112a: Decimal = Decimal("0")
    other_stcg: Decimal = Decimal("0")
    other_ltcg: Decimal = Decimal("0")


class BusinessIncomeInput(BaseModel):
    gross_receipts: Decimal = Decimal("0")
    net_profit: Decimal = Decimal("0")
    presumptive_applicable: bool = False
    books_maintained: bool = True


class DeductionClaim(BaseModel):
    section: str
    claimed_amount: Decimal
    eligible_amount: Decimal | None = None
    evidence_available: bool = False


class TaxpayerProfile(BaseModel):
    taxpayer_name: str = "Client"
    assessment_year: str = "2026-27"
    age: int = Field(default=35, ge=0, le=120)
    residential_status: str = "RESIDENT"
    has_home_loan: bool = False
    has_medical_insurance: bool = False
    has_nps: bool = False
    has_donations: bool = False
    has_education_loan: bool = False


class RecommendationRequest(BaseModel):
    tenant_id: str | None = None
    client_id: str | None = None
    profile: TaxpayerProfile = Field(default_factory=TaxpayerProfile)
    ais: AisData = Field(default_factory=AisData)
    form26as: Form26ASData = Field(default_factory=Form26ASData)
    salary: SalaryInput = Field(default_factory=SalaryInput)
    capital_gains: CapitalGainsInput = Field(default_factory=CapitalGainsInput)
    business_income: BusinessIncomeInput = Field(default_factory=BusinessIncomeInput)
    deductions_claimed: list[DeductionClaim] = Field(default_factory=list)


class RegimeComputation(BaseModel):
    regime: Regime
    gross_total_income: Decimal
    deductions_allowed: Decimal
    taxable_income: Decimal
    tax_before_cess: Decimal
    cess: Decimal
    total_tax: Decimal
    net_payable_after_credits: Decimal


class RegimeOptimization(BaseModel):
    old_regime: RegimeComputation
    new_regime: RegimeComputation
    recommended_regime: Regime
    estimated_savings: Decimal
    rationale: str


class DeductionRecommendation(BaseModel):
    section: str
    title: str
    estimated_amount: Decimal
    estimated_tax_benefit: Decimal
    confidence: Decimal = Field(ge=0, le=1)
    evidence_required: list[str] = Field(default_factory=list)
    rationale: str


class TaxSavingOpportunity(BaseModel):
    category: str
    title: str
    estimated_tax_benefit: Decimal
    priority: Literal["LOW", "MEDIUM", "HIGH"]
    action: str


class ScrutinyRisk(BaseModel):
    risk_level: RiskLevel
    score: int = Field(ge=0, le=100)
    triggers: list[str] = Field(default_factory=list)
    mitigation_actions: list[str] = Field(default_factory=list)


class AdvanceTaxSuggestion(BaseModel):
    total_tax_liability: Decimal
    credits_available: Decimal
    estimated_balance_payable: Decimal
    suggested_next_payment: Decimal
    message: str


class ConsultationSummary(BaseModel):
    executive_summary: str
    ca_review_notes: list[str] = Field(default_factory=list)
    client_action_items: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


class RecommendationResponse(BaseModel):
    profile: TaxpayerProfile
    regime_optimization: RegimeOptimization
    missing_deductions: list[DeductionRecommendation]
    tax_saving_opportunities: list[TaxSavingOpportunity]
    scrutiny_risk: ScrutinyRisk
    advance_tax_suggestions: AdvanceTaxSuggestion
    consultation_summary: ConsultationSummary
    ai_used: bool

