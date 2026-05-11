import json

from openai import OpenAI

from app.core.config import settings
from app.schemas.tax import ConsultationSummary, RecommendationRequest, RecommendationResponse


SYSTEM_PROMPT = """
You are an Indian tax intelligence assistant for a CA firm.
Use the deterministic analysis provided by the platform as source of truth.
Do not recompute tax. Do not cite unsupported legal claims.
Write concise, reviewable recommendations with clear caveats and action items.
"""


class OpenAITaxAdvisor:
    def __init__(self) -> None:
        self.enabled = bool(settings.enable_openai and settings.openai_api_key)
        self.client = OpenAI(api_key=settings.openai_api_key) if self.enabled else None

    def consultation_summary(
        self,
        request: RecommendationRequest,
        draft_response: RecommendationResponse,
    ) -> tuple[ConsultationSummary, bool]:
        if not self.enabled or self.client is None:
            return local_summary(draft_response), False

        payload = {
            "taxpayer_profile": request.profile.model_dump(mode="json"),
            "deterministic_analysis": draft_response.model_dump(mode="json", exclude={"consultation_summary"}),
        }

        response = self.client.responses.parse(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Create a structured consultation summary for this Indian tax client. "
                        "Return only the schema fields requested.\n\n"
                        f"{json.dumps(payload, ensure_ascii=True)}"
                    ),
                },
            ],
            text_format=ConsultationSummary,
        )
        return response.output_parsed, True


def local_summary(response: RecommendationResponse) -> ConsultationSummary:
    optimization = response.regime_optimization
    risk = response.scrutiny_risk
    return ConsultationSummary(
        executive_summary=(
            f"{response.profile.taxpayer_name} should use the {optimization.recommended_regime} regime, "
            f"with estimated regime savings of INR {optimization.estimated_savings}. "
            f"Scrutiny risk is {risk.risk_level} with score {risk.score}/100."
        ),
        ca_review_notes=[
            "Validate AIS, 26AS, and computation inputs before final filing.",
            "Review every recommendation with taxpayer-specific evidence.",
            *risk.mitigation_actions[:3],
        ],
        client_action_items=[
            item.action for item in response.tax_saving_opportunities[:4]
        ],
        caveats=[
            "This is an advisory estimate, not a filed return computation.",
            "Tax rules should be versioned by assessment year before production filing use.",
        ],
    )

