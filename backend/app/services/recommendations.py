import json
from decimal import Decimal

from openai import OpenAI

from app.core.config import settings
from app.db.models import AisRecord, Form26ASRecord
from app.schemas import RecommendationOut, TaxComputationOut


def generate_recommendations(
    ais: AisRecord | None,
    form26as: Form26ASRecord | None,
    computation: TaxComputationOut,
) -> list[RecommendationOut]:
    base = _rule_recommendations(ais, form26as, computation)
    if not settings.enable_openai or not settings.openai_api_key:
        return base
    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.responses.create(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": "You are an Indian CA tax advisory assistant. Return concise JSON recommendations only."},
                {"role": "user", "content": json.dumps({"ais": _safe(ais), "form26as": _safe(form26as), "computation": computation.model_dump(mode="json"), "existing": [r.model_dump(mode="json") for r in base]})},
            ],
            text={"format": {"type": "json_object"}},
        )
        payload = json.loads(response.output_text)
        extra = [
            RecommendationOut(
                title=item.get("title", "AI tax recommendation"),
                category=item.get("category", "AI"),
                priority=item.get("priority", "MEDIUM"),
                estimated_savings=Decimal(str(item.get("estimated_savings", "0"))),
                summary=item.get("summary", ""),
                payload=item,
            )
            for item in payload.get("recommendations", [])
        ]
        return base + extra[:3]
    except Exception:
        return base


def _rule_recommendations(ais: AisRecord | None, form26as: Form26ASRecord | None, computation: TaxComputationOut) -> list[RecommendationOut]:
    items = [
        RecommendationOut(
            title=f"Use {computation.recommended_regime} regime",
            category="REGIME",
            priority="HIGH",
            estimated_savings=abs(computation.old_regime_tax - computation.new_regime_tax),
            summary="Regime comparison indicates a lower estimated liability under the recommended regime.",
        )
    ]
    if ais and ais.interest_income > Decimal("10000"):
        items.append(RecommendationOut(title="Validate interest deductions and TDS", category="DEDUCTION", priority="MEDIUM", estimated_savings=Decimal("0"), summary="Interest income appears in AIS; verify deduction eligibility and tax credits."))
    if ais and ais.foreign_remittance > Decimal("250000"):
        items.append(RecommendationOut(title="Foreign remittance scrutiny pack", category="RISK", priority="HIGH", estimated_savings=Decimal("0"), summary="Prepare LRS purpose, bank advice, and source-of-funds documents."))
    if form26as and abs(form26as.mismatch_amount) > Decimal("1000"):
        items.append(RecommendationOut(title="Resolve AIS and 26AS TDS mismatch", category="MISMATCH", priority="HIGH", estimated_savings=Decimal("0"), summary="TDS/TCS credits differ between AIS and 26AS; reconcile before filing."))
    return items


def _safe(model):
    if model is None:
        return None
    return {k: str(v) for k, v in model.__dict__.items() if not k.startswith("_")}

