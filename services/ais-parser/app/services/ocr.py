from app.core.config import settings


class OcrUnavailableError(RuntimeError):
    pass


class OcrService:
    def extract_pdf_text(self, file_bytes: bytes) -> str:
        if not settings.enable_ocr:
            raise OcrUnavailableError("OCR fallback is disabled")

        try:
            from pdf2image import convert_from_bytes
            import pytesseract
        except ImportError as exc:
            raise OcrUnavailableError("OCR dependencies are not installed") from exc

        pages = convert_from_bytes(file_bytes)
        text_parts = [pytesseract.image_to_string(page, lang=settings.ocr_lang) for page in pages]
        return "\n".join(text_parts).strip()

