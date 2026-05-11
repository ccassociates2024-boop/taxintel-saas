from decimal import Decimal

from app.services.normalizer import normalize_rows, summarize


def test_normalize_extracts_required_ais_categories():
    rows = [
        {"description": "Salary paid by employer u/s 192", "amount": "10,00,000"},
        {"description": "Savings bank interest section 194A", "amount": "12,000"},
        {"description": "Dividend income 194K", "amount": "5,500"},
        {"description": "Sale of securities capital gain", "amount": "75,000"},
        {"description": "TCS on foreign remittance LRS 206C(1G)", "amount": "8,000"},
        {"description": "SFT high value credit card payment", "amount": "2,50,000"},
    ]

    transactions = normalize_rows(rows)
    summary = summarize(transactions)

    assert len(transactions) == 6
    assert summary.salary == Decimal("1000000")
    assert summary.interest_income == Decimal("12000")
    assert summary.dividend_income == Decimal("5500")
    assert summary.capital_gains == Decimal("75000")
    assert summary.foreign_remittance == Decimal("8000")
    assert summary.high_value_transactions == Decimal("250000")

