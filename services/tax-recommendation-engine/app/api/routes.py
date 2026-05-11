from fastapi import APIRouter

from app.schemas.tax import RecommendationRequest, RecommendationResponse
from app.services.engine import TaxRecommendationEngine

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/recommendations/generate", response_model=RecommendationResponse)
def generate_recommendations(request: RecommendationRequest) -> RecommendationResponse:
    return TaxRecommendationEngine().generate(request)

