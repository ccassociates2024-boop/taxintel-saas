import re
from decimal import Decimal


AMOUNT_RE = re.compile(r"(?P<amount>(?:INR\s*)?[-(]?\d[\d,]*(?:\.\d{1,2})?\)?)", re.IGNORECASE)
DATE_RE = re.compile(r"(?P<date>\d{2}[/-]\d{2}[/-]\d{4}|\d{4}-\d{2}-\d{2})")


def rows_from_text(text: str) -> list[dict]:
    rows: list[dict] = []
    for line in text.splitlines():
        clean = " ".join(line.split())
        if not clean:
            continue

        amount_match = AMOUNT_RE.search(clean)
        if not amount_match:
            continue

        date_match = DATE_RE.search(clean)
        rows.append(
            {
                "description": clean,
                "amount": amount_match.group("amount"),
                "transaction_date": date_match.group("date") if date_match else None,
            }
        )
    return rows

