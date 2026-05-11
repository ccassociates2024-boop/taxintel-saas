from app.schemas.tax import ConsultationSummary, RecommendationRequest, RecommendationResponse
from app.services.openai_client import OpenAITaxAdvisor
from app.services.rules import (
    advance_tax_suggestion,
    missing_deductions,
    optimize_regime,
    saving_opportunities,
    scrutiny_risk,
)


class TaxRecommendationEngine:
    def __init__(self, advisor: OpenAITaxAdvisor | None = None) -> None:
        self.advisor = advisor or OpenAITaxAdvisor()

    def generate(self, request: RecommendationRequest) -> RecommendationResponse:
        optimization = optimize_regime(request)
        deductions = missing_deductions(request, optimization)
        opportunities = saving_opportunities(request, optimization, deductions)
        risk = scrutiny_risk(request)
        advance_tax = advance_tax_suggestion(request, optimization)

        draft = RecommendationResponse(
            profile=request.profile,
            regime_optimization=optimization,
            missing_deductions=deductions,
            tax_saving_opportunities=opportunities,
            scrutiny_risk=risk,
            advance_tax_suggestions=advance_tax,
            consultation_summary=ConsultationSummary(executive_summary=""),
            ai_used=False,
        )
        summary, ai_used = self.advisor.consultation_summary(request, draft)
        return draft.model_copy(update={"consultation_summary": summary, "ai_used": ai_used})

