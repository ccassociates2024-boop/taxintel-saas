from typing import Any


class JsonAisParser:
    def parse(self, payload: dict[str, Any] | list[Any]) -> tuple[list[dict], list[str]]:
        rows = list(_walk_for_rows(payload))
        return rows, [] if rows else ["No AIS rows were recognized from JSON"]


def _walk_for_rows(value: Any):
    if isinstance(value, dict):
        if _looks_like_transaction(value):
            yield value
        for child in value.values():
            yield from _walk_for_rows(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_for_rows(child)


def _looks_like_transaction(row: dict[str, Any]) -> bool:
    keys = {str(key).lower().replace(" ", "_") for key in row}
    has_amount = bool(keys & {"amount", "reported_amount", "value", "transaction_amount", "tds", "tcs"})
    has_descriptor = bool(
        keys
        & {
            "category",
            "information_category",
            "description",
            "information_code",
            "section",
            "source_name",
            "reporting_entity",
        }
    )
    return has_amount and has_descriptor

