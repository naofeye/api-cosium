"""OCR and document text extraction service.

Extracts text from PDFs and images, classifies document types using
regex-based keyword matching.

Classification rules and format-specific handlers are in ocr_handlers.py.
"""

from __future__ import annotations

import io

from app.core.logging import get_logger
from app.domain.schemas.ocr import DocumentClassification, ExtractedDocument

# Re-export handlers for backward compatibility — callers importing from
# ocr_service continue to work unchanged.
from app.services.ocr_handlers import (  # noqa: F401
    CLASSIFICATION_RULES as _CLASSIFICATION_RULES,
)
from app.services.ocr_handlers import (
    classify_document,
    extract_text_from_image,
)
from app.services.ocr_handlers import (
    ocr_pdf_fallback as _ocr_pdf_fallback,
)

logger = get_logger("ocr_service")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_text_from_pdf(file_bytes: bytes) -> ExtractedDocument:
    """Extract text from a PDF file.

    Strategy: try pdfplumber first (native text). If the result is mostly
    empty (scanned PDF), fall back to pdf2image + pytesseract OCR.
    """
    import pdfplumber

    text_parts: list[str] = []
    page_count = 0

    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            page_count = len(pdf.pages)
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text_parts.append(page_text)
    except Exception as exc:  # noqa: BLE001 — un PDF corrompu ne doit pas aborter, fallback OCR
        logger.warning("pdfplumber_extraction_failed", error=str(exc), error_type=type(exc).__name__)

    native_text = "\n".join(text_parts).strip()

    # If native extraction yielded enough text, return it
    if len(native_text) > 50:
        logger.info(
            "pdf_text_extracted",
            method="pdfplumber",
            page_count=page_count,
            text_length=len(native_text),
        )
        return ExtractedDocument(
            raw_text=native_text,
            page_count=page_count,
            extraction_method="pdfplumber",
            confidence=None,
            language="fra",
        )

    # Fallback: OCR via pdf2image + pytesseract
    return _ocr_pdf_fallback(file_bytes, page_count)


def extract_and_classify(
    file_bytes: bytes, filename: str
) -> tuple[ExtractedDocument, DocumentClassification]:
    """Convenience: extract text then classify in one call."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf":
        extracted = extract_text_from_pdf(file_bytes)
    elif ext in ("jpg", "jpeg", "png", "tiff", "bmp"):
        extracted = extract_text_from_image(file_bytes)
    else:
        logger.warning("unsupported_file_type", filename=filename, extension=ext)
        extracted = ExtractedDocument(
            raw_text="",
            page_count=0,
            extraction_method="none",
            confidence=None,
            language="fra",
        )

    classification = classify_document(extracted.raw_text)
    return extracted, classification
