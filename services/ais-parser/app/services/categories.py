from enum import StrEnum


class AisCategory(StrEnum):
    SALARY = "salary"
    INTEREST_INCOME = "interest_income"
    CAPITAL_GAINS = "capital_gains"
    DIVIDEND_INCOME = "dividend_income"
    TDS_TCS = "tds_tcs"
    FOREIGN_REMITTANCE = "foreign_remittance"
    HIGH_VALUE_TRANSACTIONS = "high_value_transactions"


CATEGORY_KEYWORDS: dict[AisCategory, tuple[str, ...]] = {
    AisCategory.SALARY: ("salary", "sec 192", "section 192", "employer"),
    AisCategory.INTEREST_INCOME: ("interest", "savings bank", "deposit", "sec 194a", "194a"),
    AisCategory.CAPITAL_GAINS: ("capital gain", "securities", "mutual fund", "equity", "sale of securities"),
    AisCategory.DIVIDEND_INCOME: ("dividend", "sec 194k", "194k"),
    AisCategory.FOREIGN_REMITTANCE: ("foreign remittance", "lrs", "remittance", "section 206c(1g)", "206c(1g)"),
    AisCategory.TDS_TCS: ("tds", "tcs", "tax deducted", "tax collected"),
    AisCategory.HIGH_VALUE_TRANSACTIONS: (
        "sft",
        "high value",
        "cash deposit",
        "purchase of immovable property",
        "credit card",
    ),
}


def classify_explicit_category(value: object) -> AisCategory | None:
    text = str(value or "").lower()
    explicit_priority = (
        AisCategory.FOREIGN_REMITTANCE,
        AisCategory.TDS_TCS,
        AisCategory.SALARY,
        AisCategory.INTEREST_INCOME,
        AisCategory.CAPITAL_GAINS,
        AisCategory.DIVIDEND_INCOME,
        AisCategory.HIGH_VALUE_TRANSACTIONS,
    )
    for category in explicit_priority:
        if any(keyword in text for keyword in CATEGORY_KEYWORDS[category]):
            return category
    return None


def classify_category(*values: object) -> AisCategory | None:
    searchable = " ".join(str(value or "").lower() for value in values)
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in searchable for keyword in keywords):
            return category
    return None
