from io import BytesIO

import pandas as pd


class ExcelAisParser:
    def parse(self, file_bytes: bytes) -> tuple[list[dict], list[str]]:
        warnings: list[str] = []
        workbook = pd.read_excel(BytesIO(file_bytes), sheet_name=None, dtype=object)
        rows: list[dict] = []

        for sheet_name, frame in workbook.items():
            frame = frame.dropna(how="all")
            if frame.empty:
                continue
            frame.columns = [str(column).strip().lower().replace(" ", "_") for column in frame.columns]
            for row in frame.to_dict(orient="records"):
                clean_row = {key: value for key, value in row.items() if pd.notna(value)}
                clean_row["sheet_name"] = sheet_name
                rows.append(clean_row)

        if not rows:
            warnings.append("No AIS rows were recognized from Excel workbook")
        return rows, warnings

