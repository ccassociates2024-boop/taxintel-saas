from decimal import Decimal

from app.schemas.tax import (
    AdvanceTaxSuggestion,
    DeductionRecommendation,
    RecommendationRequest,
    RegimeOptimization,
    ScrutinyRisk,
    TaxSavingOpportunity,
)
from app.services.tax_math import compute_regime, money, total_tax_credits


def optimize_regime(request: RecommendationRequest) -> RegimeOptimization:
    old_regime = compute_regime(request, "OLD")
    new_regime = compute_regime(request, "NEW")
    recommended = "OLD" if old_regime.total_tax <= new_regime.total_tax else "NEW"
    savings = abs(old_regime.total_tax - new_regime.total_tax)
    rationale = (
        "Old regime is better because deductions and exemptions reduce taxable income materially."
        if recommended == "OLD"
        else "New regime is better because lower slab rates outperform available deductions."
    )
    return RegimeOptimization(
        old_regime=old_regime,
        new_regime=new_regime,
        recommended_regime=recommended,  # type: ignore[arg-type]
        estimated_savings=money(savings),
        rationale=rationale,
    )


def missing_deductions(request: RecommendationRequest, optimization: RegimeOptimization) -> list[DeductionRecommendation]:
    if optimization.recommended_regime == "NEW":
        return []

    claimed_sections = {item.section.upper().replace(" ", "") for item in request.deductions_claimed}
    taxable_income = optimization.old_regime.taxable_income
    marginal_rate = _marginal_rate(taxable_income)
    findings: list[DeductionRecommendation] = []

    def add(section: str, title: str, amount: Decimal, evidence: list[str], rationale: str, confidence: str) -> None:
        if section not in claimed_sections and amount > 0:
            findings.append(
                DeductionRecommendation(
                    section=section,
                    title=title,
                    estimated_amount=amount,
                    estimated_tax_benefit=money(amount * marginal_rate),
                    confidence=Decimal(confidence),
                    evidence_required=evidence,
                    rationale=rationale,
                )
            )

    add(
        "80D",
        "Medical insurance deduction",
        Decimal("25000") if request.profile.has_medical_insurance else Decimal("0"),
        ["Insurance premium receipt", "Bank payment proof"],
        "Profile indicates medical insurance but no 80D claim was supplied.",
        "0.86",
    )
    add(
        "80CCD(1B)",
        "Additional NPS deduction",
        Decimal("50000") if request.profile.has_nps else Decimal("0"),
        ["NPS contribution statement"],
        "NPS flag is present and additional 80CCD(1B) claim is missing.",
        "0.82",
    )
    add(
        "24B",
        "Home loan interest deduction",
        Decimal("200000") if request.profile.has_home_loan else Decimal("0"),
        ["Home loan interest certificate", "Possession details"],
        "Home loan indicator is present and section 24(b) claim is missing.",
        "0.78",
    )
    add(
        "80E",
        "Education loan interest deduction",
        Decimal("75000") if request.profile.has_education_loan else Decimal("0"),
        ["Education loan interest certificate"],
        "Education loan indicator is present and 80E should be reviewed.",
        "0.72",
    )
    return findings


def saving_opportunities(
    request: RecommendationRequest,
    optimization: RegimeOptimization,
    deductions: list[DeductionRecommendation],
) -> list[TaxSavingOpportunity]:
    opportunities = [
        TaxSavingOpportunity(
            category="REGIME",
            title=f"Select {optimization.recommended_regime} regime",
            estimated_tax_benefit=optimization.estimated_savings,
            priority="HIGH" if optimization.estimated_savings >= Decimal("25000") else "MEDIUM",
            action="Confirm regime selection after validating final deductions and credits.",
        )
    ]
    for item in deductions:
        opportunities.append(
            TaxSavingOpportunity(
                category="DEDUCTION",
                title=item.title,
                estimated_tax_benefit=item.estimated_tax_benefit,
                priority="HIGH" if item.estimated_tax_benefit >= Decimal("25000") else "MEDIUM",
                action=f"Collect evidence and validate claim under section {item.section}.",
            )
        )

    if request.business_income.presumptive_applicable and request.business_income.books_maintained:
        opportunities.append(
            TaxSavingOpportunity(
                category="BUSINESS_INCOME",
                title="Evaluate presumptive taxation",
                estimated_tax_benefit=Decimal("0"),
                priority="MEDIUM",
                action="Compare book-profit tax result with presumptive scheme eligibility before filing.",
            )
        )
    return opportunities


def scrutiny_risk(request: RecommendationRequest) -> ScrutinyRisk:
    triggers: list[str] = []
    mitigation: list[str] = []
    score = 10

    capital_gap = request.ais.capital_gains - (
        request.capital_gains.stcg_equity_111a
        + request.capital_gains.ltcg_equity_112a
        + request.capital_gains.other_stcg
        + request.capital_gains.other_ltcg
    )
    if abs(capital_gap) >= Decimal("50000"):
        score += 25
        triggers.append("AIS capital gains differ materially from reported capital gains.")
        mitigation.append("Reconcile broker statements, AIS securities data, and grandfathering calculations.")

    if request.ais.foreign_remittance >= Decimal("250000") and request.profile.residential_status.upper() == "RESIDENT":
        score += 20
        triggers.append("Foreign remittance is visible in AIS and needs source/purpose support.")
        mitigation.append("Keep LRS bank advice, Form A2, and source-of-funds documentation.")

    credits_26as = request.form26as.salary_tds + request.form26as.non_salary_tds + request.form26as.tcs
    if abs(request.ais.tds_tcs - credits_26as) >= Decimal("10000"):
        score += 18
        triggers.append("AIS TDS/TCS does not match 26AS credits.")
        mitigation.append("Validate deductor TAN entries and tax credit booking status in 26AS.")

    if request.ais.high_value_transactions >= Decimal("1000000"):
        score += 18
        triggers.append("High-value SFT transactions require income-source traceability.")
        mitigation.append("Map each SFT item to bank, investment, or property documentation.")

    if request.business_income.gross_receipts >= Decimal("1000000") and request.business_income.net_profit <= 0:
        score += 12
        triggers.append("Business receipts exist but no positive profit is reported.")
        mitigation.append("Prepare expense ledger, bank reconciliation, and loss explanation.")

    score = min(score, 100)
    risk = "HIGH" if score >= 70 else "MEDIUM" if score >= 35 else "LOW"
    return ScrutinyRisk(
        risk_level=risk,  # type: ignore[arg-type]
        score=score,
        triggers=triggers,
        mitigation_actions=mitigation,
    )


def advance_tax_suggestion(request: RecommendationRequest, optimization: RegimeOptimization) -> AdvanceTaxSuggestion:
    selected = optimization.old_regime if optimization.recommended_regime == "OLD" else optimization.new_regime
    credits = total_tax_credits(request)
    balance = money(max(Decimal("0"), selected.total_tax - credits))
    payment = money(balance)
    message = (
        "No additional advance tax appears necessary based on current credits."
        if payment == 0
        else "Pay the estimated balance promptly to reduce interest exposure under advance tax provisions."
    )
    return AdvanceTaxSuggestion(
        total_tax_liability=selected.total_tax,
        credits_available=credits,
        estimated_balance_payable=balance,
        suggested_next_payment=payment,
        message=message,
    )


def _marginal_rate(taxable_income: Decimal) -> Decimal:
    if taxable_income > Decimal("1000000"):
        return Decimal("0.312")
    if taxable_income > Decimal("500000"):
        return Decimal("0.208")
    return Decimal("0.052")

