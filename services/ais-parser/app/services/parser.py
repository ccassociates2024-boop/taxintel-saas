import hashlib
import json
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.schemas.ais import AisParseResult
from app.core.config import settings
from app.services.excel_parser import ExcelAisParser
from app.services.json_parser import JsonAisParser
from app.services.normalizer import normalize_rows, summarize
from app.services.pdf_parser import PdfAisParser


class AisParserService:
    async def parse_upload(self, file: UploadFile, assessment_year: str) -> tuple[AisParseResult, str]:
        file_bytes = await file.read()
        max_bytes = settings.max_upload_mb * 1024 * 1024
        if len(file_bytes) > max_bytes:
            raise HTTPException(status_code=413, detail=f"AIS file exceeds {settings.max_upload_mb} MB limit")

        file_hash = hashlib.sha256(file_bytes).hexdigest()
        extension = Path(file.filename or "").suffix.lower()

        if extension == ".pdf":
            rows, warnings = PdfAisParser().parse(file_bytes)
        elif extension == ".json":
            try:
                payload = json.loads(file_bytes.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=400, detail="Invalid JSON AIS file") from exc
            rows, warnings = JsonAisParser().parse(payload)
        elif extension in {".xlsx", ".xlsm", ".xls"}:
            rows, warnings = ExcelAisParser().parse(file_bytes)
        else:
            raise HTTPException(status_code=415, detail="Unsupported AIS file type")

        transactions = normalize_rows(rows)
        result = AisParseResult(
            assessment_year=assessment_year,
            summary=summarize(transactions),
            transactions=transactions,
            warnings=warnings,
            raw_payload={"file_name": file.filename, "row_count": len(rows), "source": extension.removeprefix(".")},
        )
        return result, file_hash
