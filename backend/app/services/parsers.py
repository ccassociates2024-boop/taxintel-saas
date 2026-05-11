import json
import re
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pandas as pd
from pypdf import PdfReader

from app.schemas import AisSummary, Form26ASSummary


AMOUNT_RE = re.compile(r"[-(]?\d[\d,]*(?:\.\d{1,2})?\)?")


def parse_ais(file_bytes: bytes, filename: str) -> AisSummary:
    rows = _rows(file_bytes, filename)
    summary = AisSummary()
    for row in rows:
        text = " ".join(str(v).lower() for v in row.values())
        amount = _amount(row)
        if amount == 0:
            continue
        if "salary" in text or "section 192" in text:
            summary.salary += amount
        elif "dividend" in text or "194k" in text:
            summary.dividend_income += amount
        elif "capital gain" in text or "securities" in text or "mutual fund" in text:
            summary.capital_gains += amount
        elif "tds" in text or "tcs" in text or "tax deducted" in text:
            summary.tds_tcs += amount
        elif "foreign remittance" in text or "lrs" in text or "206c(1g)" in text:
            summary.foreign_remittance += amount
        elif "sft" in text or "high value" in text or "cash deposit" in text:
            summary.high_value_transactions += amount
        elif "interest" in text or "194a" in text or "deposit" in text:
            summary.interest_income += amount
    return summary


def parse_26as(file_bytes: bytes, filename: str, ais: AisSummary | None = None) -> Form26ASSummary:
    rows = _rows(file_bytes, filename)
    summary = Form26ASSummary()
    for row in rows:
        text = " ".join(str(v).lower() for v in row.values())
        amount = _amount(row)
        if amount == 0:
            continue
        if "192" in text or "salary" in text:
            summary.salary_tds += amount
        elif "tcs" in text:
            summary.tcs += amount
        elif "advance tax" in text:
            summary.advance_tax_paid += amount
        elif "tds" in text or "194" in text:
            summary.non_salary_tds += amount
    if ais:
        summary.mismatch_amount = ais.tds_tcs - (summary.salary_tds + summary.non_salary_tds + summary.tcs)
    return summary


def _rows(file_bytes: bytes, filename: str) -> list[dict]:
    ext = Path(filename).suffix.lower()
    if ext == ".json":
        return list(_walk(json.loads(file_bytes.decode("utf-8"))))
    if ext in {".xlsx", ".xlsm", ".xls"}:
        frames = pd.read_excel(BytesIO(file_bytes), sheet_name=None, dtype=object)
        rows: list[dict] = []
        for _, frame in frames.items():
            frame.columns = [str(c).strip().lower().replace(" ", "_") for c in frame.columns]
            rows.extend({k: v for k, v in row.items() if pd.notna(v)} for row in frame.to_dict("records"))
        return rows
    if ext == ".pdf":
        reader = PdfReader(BytesIO(file_bytes))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        return [{"description": line, "amount": match.group(0)} for line in text.splitlines() if (match := AMOUNT_RE.search(line))]
    return []


def _walk(value):
    if isinstance(value, dict):
        if any(k.lower().replace(" ", "_") in {"amount", "reported_amount", "tds", "tcs", "value"} for k in value):
            yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _amount(row: dict) -> Decimal:
    for key, value in row.items():
        if str(key).lower().replace(" ", "_") in {"amount", "reported_amount", "tds", "tcs", "tax_deposited", "value"}:
            return _decimal(value)
    for value in row.values():
        match = AMOUNT_RE.search(str(value))
        if match:
            return _decimal(match.group(0))
    return Decimal("0")


def _decimal(value) -> Decimal:
    text = str(value).replace(",", "").replace("INR", "").strip()
    if text.startswith("(") and text.endswith(")"):
        text = f"-{text[1:-1]}"
    try:
        return Decimal(text)
    except Exception:
        return Decimal("0")

