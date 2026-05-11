from decimal import Decimal

from app.schemas.ais import AisParseResult, DeclaredTaxData, MismatchFinding


SEVERITY_THRESHOLDS = (
    (Decimal("100000"), "HIGH"),
    (Decimal("25000"), "MEDIUM"),
    (Decimal("0"), "LOW"),
)


def detect_mismatches(
    ais_result: AisParseResult,
    declared: DeclaredTaxData,
    *,
    absolute_tolerance: Decimal = Decimal("100"),
    percentage_tolerance: Decimal = Decimal("0.01"),
) -> list[MismatchFinding]:
    findings: list[MismatchFinding] = []
    summary = ais_result.summary.model_dump()
    declared_map = declared.model_dump()

    for category, ais_amount in summary.items():
        declared_amount = Decimal(declared_map.get(category, Decimal("0")))
        difference = Decimal(ais_amount) - declared_amount
        tolerance = max(absolute_tolerance, abs(Decimal(ais_amount)) * percentage_tolerance)
        if abs(difference) <= tolerance:
            continue

        findings.append(
            MismatchFinding(
                category=category,
                severity=_severity(abs(difference)),
                ais_amount=Decimal(ais_amount),
                declared_amount=declared_amount,
                difference=difference,
                message=_message(category, difference),
                evidence={
                    "assessment_year": ais_result.assessment_year,
                    "tolerance": str(tolerance),
                    "transaction_count": sum(1 for txn in ais_result.transactions if txn.category == category),
                },
            )
        )
    return findings


def _severity(abs_difference: Decimal) -> str:
    for threshold, severity in SEVERITY_THRESHOLDS:
        if abs_difference >= threshold:
            return severity
    return "LOW"


def _message(category: str, difference: Decimal) -> str:
    direction = "higher than" if difference > 0 else "lower than"
    label = category.replace("_", " ")
    return f"AIS {label} is {direction} declared value by INR {abs(difference):,.2f}."

