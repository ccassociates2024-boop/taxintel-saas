from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.schemas.ais import AisSummary, AisTransactionOut
from app.services.categories import AisCategory, classify_category, classify_explicit_category


AMOUNT_KEYS = ("amount", "reported_amount", "value", "transaction_amount", "tax_deposited", "tds", "tcs")
DATE_KEYS = ("transaction_date", "date", "payment_date", "reported_date")
SOURCE_KEYS = ("source_name", "deductor", "deductor_name", "reporting_entity", "payer", "employer")
CODE_KEYS = ("information_code", "info_code", "section", "code")


def to_decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    try:
        normalized = str(value).replace(",", "").replace("INR", "").strip()
        if normalized.startswith("(") and normalized.endswith(")"):
            normalized = f"-{normalized[1:-1]}"
        return Decimal(normalized)
    except (InvalidOperation, ValueError):
        return Decimal("0")


def parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%b-%Y", "%d %b %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def first_present(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
    lower_row = {str(key).strip().lower().replace(" ", "_"): value for key, value in row.items()}
    for key in keys:
        if key in lower_row and lower_row[key] not in (None, ""):
            return lower_row[key]
    return None


def normalize_rows(rows: list[dict[str, Any]]) -> list[AisTransactionOut]:
    transactions: list[AisTransactionOut] = []
    for row in rows:
        lower_row = {str(key).strip().lower().replace(" ", "_"): value for key, value in row.items()}
        category = (
            classify_explicit_category(lower_row.get("category"))
            or classify_explicit_category(lower_row.get("information_category"))
            or classify_category(
                lower_row.get("description"),
                lower_row.get("information_code"),
                lower_row.get("section"),
                row,
            )
        )
        if not category:
            continue

        amount = to_decimal(first_present(row, AMOUNT_KEYS))
        if amount == 0:
            continue

        transactions.append(
            AisTransactionOut(
                category=category.value,
                amount=amount,
                transaction_date=parse_date(first_present(row, DATE_KEYS)),
                source_name=first_present(row, SOURCE_KEYS),
                information_code=first_present(row, CODE_KEYS),
                confidence=Decimal("0.88") if category != AisCategory.HIGH_VALUE_TRANSACTIONS else Decimal("0.80"),
                raw=row,
            )
        )
    return transactions


def summarize(transactions: list[AisTransactionOut]) -> AisSummary:
    totals = {category.value: Decimal("0") for category in AisCategory}
    for txn in transactions:
        totals[txn.category] += txn.amount
    return AisSummary(**totals)
