from app.services.normalizer import normalize_rows
from app.services.ocr import OcrService
from app.services.text_table_parser import rows_from_text


class PdfAisParser:
    def __init__(self, ocr_service: OcrService | None = None):
        self.ocr_service = ocr_service or OcrService()

    def parse(self, file_bytes: bytes) -> tuple[list[dict], list[str]]:
        warnings: list[str] = []
        text = self._extract_text(file_bytes)

        if len(text.strip()) < 25:
            warnings.append("PDF text extraction was empty; OCR fallback was used")
            text = self.ocr_service.extract_pdf_text(file_bytes)

        rows = rows_from_text(text)
        normalized = normalize_rows(rows)
        if not normalized:
            warnings.append("No AIS rows were recognized from PDF text")
        return [txn.raw for txn in normalized], warnings

    @staticmethod
    def _extract_text(file_bytes: bytes) -> str:
        from io import BytesIO

        from pypdf import PdfReader

        reader = PdfReader(BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

