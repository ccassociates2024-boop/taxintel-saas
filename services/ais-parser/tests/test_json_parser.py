from app.services.json_parser import JsonAisParser
from app.services.normalizer import normalize_rows


def test_json_parser_finds_nested_transactions():
    payload = {
        "ais": {
            "parts": [
                {"information_category": "Salary", "reported_amount": "900000", "source_name": "ABC Pvt Ltd"},
                {"information_category": "TDS", "tds": "45000", "section": "192"},
            ]
        }
    }

    rows, warnings = JsonAisParser().parse(payload)
    transactions = normalize_rows(rows)

    assert warnings == []
    assert len(rows) == 2
    assert {txn.category for txn in transactions} == {"salary", "tds_tcs"}

