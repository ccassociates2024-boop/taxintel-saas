from decimal import Decimal

from app.schemas.ais import AisParseResult, AisSummary, DeclaredTaxData
from app.services.mismatch import detect_mismatches


def test_detect_mismatches_respects_tolerance_and_severity():
    result = AisParseResult(
        assessment_year="2026-27",
        summary=AisSummary(salary=Decimal("1000000"), interest_income=Decimal("10000")),
        transactions=[],
    )
    declared = DeclaredTaxData(salary=Decimal("850000"), interest_income=Decimal("9995"))

    findings = detect_mismatches(result, declared)

    assert len(findings) == 1
    assert findings[0].category == "salary"
    assert findings[0].severity == "HIGH"
    assert findings[0].difference == Decimal("150000")

