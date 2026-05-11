from decimal import Decimal

from app.schemas.tax import DeductionClaim, RecommendationRequest, SalaryInput
from app.services.rules import optimize_regime


def test_old_regime_wins_when_deductions_are_large():
    request = RecommendationRequest(
        salary=SalaryInput(gross_salary=Decimal("1500000")),
        deductions_claimed=[
            DeductionClaim(section="80C", claimed_amount=Decimal("150000")),
            DeductionClaim(section="24B", claimed_amount=Decimal("200000")),
            DeductionClaim(section="80G", claimed_amount=Decimal("500000")),
        ],
    )

    result = optimize_regime(request)

    assert result.recommended_regime == "OLD"
    assert result.old_regime.deductions_allowed == Decimal("850000")


def test_new_regime_wins_with_no_deductions():
    request = RecommendationRequest(salary=SalaryInput(gross_salary=Decimal("900000")))

    result = optimize_regime(request)

    assert result.recommended_regime == "NEW"
    assert result.estimated_savings > 0
