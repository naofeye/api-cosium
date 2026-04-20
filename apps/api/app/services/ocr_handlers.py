"""Format-specific OCR handlers and classification rules.

Extracted from ocr_service.py to keep files under 300 lines.
Contains: classification keyword rules, PDF OCR fallback, image extraction.
"""

from __future__ import annotations

import io
import re

from app.core.logging import get_logger
from app.domain.schemas.ocr import DocumentClassification, ExtractedDocument
from app.services.ocr_classification_rules import CLASSIFICATION_RULES

logger = get_logger("ocr_handlers")


def ocr_pdf_fallback(file_bytes: bytes, page_count_hint: int) -> ExtractedDocument:
    """OCR fallback for scanned PDFs."""
    import pytesseract
    from pdf2image import convert_from_bytes

    images = convert_from_bytes(file_bytes, dpi=300)
    page_count = len(images)
    text_parts: list[str] = []
    confidences: list[float] = []

    for img in images:
        data = pytesseract.image_to_data(img, lang="fra", output_type=pytesseract.Output.DICT)
        page_text = " ".join(
            word for word, conf in zip(data["text"], data["conf"], strict=False) if int(conf) > 0 and word.strip()
        )
        text_parts.append(page_text)

        valid_confs = [int(c) for c in data["conf"] if int(c) > 0]
        if valid_confs:
            confidences.append(sum(valid_confs) / len(valid_confs) / 100.0)

    raw_text = "\n".join(text_parts).strip()
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    logger.info(
        "pdf_ocr_extracted",
        method="tesseract",
        page_count=page_count,
        text_length=len(raw_text),
        confidence=round(avg_confidence, 3),
    )

    return ExtractedDocument(
        raw_text=raw_text,
        page_count=page_count,
        extraction_method="pdfplumber+tesseract",
        confidence=round(avg_confidence, 3),
        language="fra",
    )


def extract_text_from_image(file_bytes: bytes) -> ExtractedDocument:
    """Extract text from an image file (JPG, PNG, TIFF) using Tesseract OCR."""
    import pytesseract
    from PIL import Image

    img = Image.open(io.BytesIO(file_bytes))
    data = pytesseract.image_to_data(img, lang="fra", output_type=pytesseract.Output.DICT)

    words = []
    valid_confs: list[int] = []
    for word, conf in zip(data["text"], data["conf"], strict=False):
        c = int(conf)
        if c > 0 and word.strip():
            words.append(word)
            valid_confs.append(c)

    raw_text = " ".join(words)
    avg_confidence = sum(valid_confs) / len(valid_confs) / 100.0 if valid_confs else 0.0

    logger.info(
        "image_ocr_extracted",
        method="tesseract",
        text_length=len(raw_text),
        confidence=round(avg_confidence, 3),
    )

    return ExtractedDocument(
        raw_text=raw_text,
        page_count=1,
        extraction_method="tesseract",
        confidence=round(avg_confidence, 3),
        language="fra",
    )


def classify_document(text: str) -> DocumentClassification:
    """Classify a document type based on keyword matching in extracted text.

    Returns the best-matching type with confidence and keywords found.
    """
    if not text or not text.strip():
        return DocumentClassification(
            document_type="autre",
            confidence=0.0,
            keywords_found=[],
        )

    text_lower = text.lower()
    best_type = "autre"
    best_score = 0.0
    best_keywords: list[str] = []

    for doc_type, keywords in CLASSIFICATION_RULES:
        found: list[str] = []
        for kw in keywords:
            if re.search(kw, text_lower):
                found.append(kw)

        if found:
            score = len(found) / len(keywords)
            if score > best_score:
                best_score = score
                best_type = doc_type
                best_keywords = found

    logger.info(
        "document_classified",
        document_type=best_type,
        confidence=round(best_score, 3),
        keywords_count=len(best_keywords),
    )

    return DocumentClassification(
        document_type=best_type,
        confidence=round(min(best_score, 1.0), 3),
        keywords_found=best_keywords,
    )
