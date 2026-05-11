from decimal import Decimal

from app.schemas.tax import RecommendationRequest, SalaryInput, TaxpayerProfile
from app.services.engine import TaxRecommendationEngine


def test_engine_generates_local_summary_without_openai():
    request = RecommendationRequest(
        profile=TaxpayerProfile(taxpayer_name="Aarav Mehta", has_medical_insurance=True),
        salary=SalaryInput(gross_salary=Decimal("1200000")),
    )

    response = TaxRecommendationEngine().generate(request)

    assert response.ai_used is False
    assert response.regime_optimization.recommended_regime in {"OLD", "NEW"}
    assert response.consultation_summary.executive_summary

