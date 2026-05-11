from decimal import Decimal, ROUND_HALF_UP

from app.schemas.tax import DeductionClaim, RecommendationRequest, RegimeComputation


CESS_RATE = Decimal("0.04")
STANDARD_DEDUCTION_CAP = Decimal("50000")
NEW_REGIME_STANDARD_DEDUCTION_CAP = Decimal("75000")
EQUITY_LTCG_EXEMPTION = Decimal("125000")


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def compute_gross_total_income(request: RecommendationRequest) -> Decimal:
    salary_income = max(
        Decimal("0"),
        request.salary.gross_salary
        - min(request.salary.standard_deduction, STANDARD_DEDUCTION_CAP)
        - request.salary.hra_exemption
        - request.salary.professional_tax,
    )
    capital_gains = (
        request.capital_gains.stcg_equity_111a
        + max(Decimal("0"), request.capital_gains.ltcg_equity_112a - EQUITY_LTCG_EXEMPTION)
        + request.capital_gains.other_stcg
        + request.capital_gains.other_ltcg
    )
    return money(
        salary_income
        + request.ais.interest_income
        + request.ais.dividend_income
        + capital_gains
        + request.business_income.net_profit
    )


def deduction_total(deductions: list[DeductionClaim], *, regime: str) -> Decimal:
    if regime == "NEW":
        return Decimal("0")

    caps = {
        "80C": Decimal("150000"),
        "80CCD(1B)": Decimal("50000"),
        "80D": Decimal("25000"),
        "80E": Decimal("999999999"),
        "80G": Decimal("999999999"),
        "24B": Decimal("200000"),
    }
    total = Decimal("0")
    for item in deductions:
        section = item.section.upper().replace(" ", "")
        eligible = item.eligible_amount if item.eligible_amount is not None else item.claimed_amount
        total += min(item.claimed_amount, eligible, caps.get(section, item.claimed_amount))
    return money(total)


def compute_regime(request: RecommendationRequest, regime: str) -> RegimeComputation:
    gross_income = compute_gross_total_income(request)
    if regime == "NEW":
        new_salary_relief = min(request.salary.gross_salary, NEW_REGIME_STANDARD_DEDUCTION_CAP)
        gross_income = max(Decimal("0"), gross_income - max(Decimal("0"), new_salary_relief - STANDARD_DEDUCTION_CAP))

    deductions = deduction_total(request.deductions_claimed, regime=regime)
    taxable_income = money(max(Decimal("0"), gross_income - deductions))
    tax_before_cess = money(_slab_tax(taxable_income, regime))
    cess = money(tax_before_cess * CESS_RATE)
    total_tax = money(tax_before_cess + cess)
    credits = total_tax_credits(request)

    return RegimeComputation(
        regime=regime,  # type: ignore[arg-type]
        gross_total_income=gross_income,
        deductions_allowed=deductions,
        taxable_income=taxable_income,
        tax_before_cess=tax_before_cess,
        cess=cess,
        total_tax=total_tax,
        net_payable_after_credits=money(total_tax - credits),
    )


def total_tax_credits(request: RecommendationRequest) -> Decimal:
    return money(
        request.ais.tds_tcs
        + request.form26as.salary_tds
        + request.form26as.non_salary_tds
        + request.form26as.tcs
        + request.form26as.advance_tax_paid
        + request.form26as.self_assessment_tax_paid
    )


def _slab_tax(income: Decimal, regime: str) -> Decimal:
    if income <= Decimal("700000") and regime == "NEW":
        return Decimal("0")
    if income <= Decimal("500000") and regime == "OLD":
        return Decimal("0")

    slabs = (
        [
            (Decimal("300000"), Decimal("0")),
            (Decimal("700000"), Decimal("0.05")),
            (Decimal("1000000"), Decimal("0.10")),
            (Decimal("1200000"), Decimal("0.15")),
            (Decimal("1500000"), Decimal("0.20")),
            (Decimal("999999999"), Decimal("0.30")),
        ]
        if regime == "NEW"
        else [
            (Decimal("250000"), Decimal("0")),
            (Decimal("500000"), Decimal("0.05")),
            (Decimal("1000000"), Decimal("0.20")),
            (Decimal("999999999"), Decimal("0.30")),
        ]
    )

    tax = Decimal("0")
    previous_limit = Decimal("0")
    remaining = income
    for upper_limit, rate in slabs:
        slab_amount = min(remaining, upper_limit - previous_limit)
        if slab_amount <= 0:
            break
        tax += slab_amount * rate
        remaining -= slab_amount
        previous_limit = upper_limit
    return tax

