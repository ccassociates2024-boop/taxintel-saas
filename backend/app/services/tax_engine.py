from decimal import Decimal, ROUND_HALF_UP

from app.schemas import ComputeRequest, TaxComputationOut


CESS = Decimal("0.04")


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def compute_tax(payload: ComputeRequest) -> TaxComputationOut:
    gross = payload.salary + payload.business_income + payload.house_property_income + payload.capital_gains
    old_taxable = max(Decimal("0"), gross - Decimal("50000") - payload.deductions)
    new_taxable = max(Decimal("0"), gross - Decimal("75000"))
    old_tax = money(_slab(old_taxable, "OLD") * (Decimal("1") + CESS))
    new_tax = money(_slab(new_taxable, "NEW") * (Decimal("1") + CESS))
    interest = _interest(payload)
    recommended = "OLD" if old_tax <= new_tax else "NEW"
    selected_tax = min(old_tax, new_tax) + interest
    net = money(selected_tax - payload.tax_credits)
    payable = max(Decimal("0"), net)
    refund = abs(min(Decimal("0"), net))
    health = 92 if payable == 0 else 78 if payable < Decimal("50000") else 62
    return TaxComputationOut(
        assessment_year=payload.assessment_year,
        old_regime_tax=old_tax,
        new_regime_tax=new_tax,
        recommended_regime=recommended,
        tax_payable=payable,
        refund_estimate=refund,
        health_score=health,
        computation_json={
            "gross_total_income": str(gross),
            "old_taxable_income": str(old_taxable),
            "new_taxable_income": str(new_taxable),
            "interest_234abc": str(interest),
            "cess_rate": str(CESS),
        },
    )


def _slab(income: Decimal, regime: str) -> Decimal:
    if regime == "NEW" and income <= Decimal("700000"):
        return Decimal("0")
    if regime == "OLD" and income <= Decimal("500000"):
        return Decimal("0")
    slabs = (
        [(300000, 0), (700000, 0.05), (1000000, 0.10), (1200000, 0.15), (1500000, 0.20), (999999999, 0.30)]
        if regime == "NEW"
        else [(250000, 0), (500000, 0.05), (1000000, 0.20), (999999999, 0.30)]
    )
    tax = Decimal("0")
    prev = Decimal("0")
    remaining = income
    for limit, rate in slabs:
        upper = Decimal(str(limit))
        slab_amount = min(remaining, upper - prev)
        if slab_amount <= 0:
            break
        tax += slab_amount * Decimal(str(rate))
        remaining -= slab_amount
        prev = upper
    return tax


def _interest(payload: ComputeRequest) -> Decimal:
    interest_234a = payload.tax_credits * Decimal("0.01") * Decimal(payload.filing_delay_months)
    interest_234bc = payload.advance_tax_shortfall * Decimal("0.03")
    return money(max(Decimal("0"), interest_234a + interest_234bc))

