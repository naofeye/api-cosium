"""OCR and document text extraction service.

Extracts text from PDFs and images, classifies document types using
regex-based keyword matching.
"""

from __future__ import annotations

import io
import re

from app.core.logging import get_logger
from app.domain.schemas.ocr import DocumentClassification, ExtractedDocument

logger = get_logger("ocr_service")

# ---------------------------------------------------------------------------
# Keyword sets for classification
# ---------------------------------------------------------------------------

_CLASSIFICATION_RULES: list[tuple[str, list[str]]] = [
    (
        "ordonnance",
        [
            "ordonnance",
            "prescription",
            "sphere",
            "cylindre",
            "addition",
            r"\bOD\b",
            r"\bOG\b",
            "acuite",
            "correction",
            "dioptrie",
            "oeil droit",
            "oeil gauche",
        ],
    ),
    (
        "devis",
        [
            "devis",
            "montant ttc",
            "montant ht",
            "reste a charge",
            r"part\s+(secu|mutuelle)",
            "total ttc",
            "monture",
            "verres",
            "equipement optique",
        ],
    ),
    (
        "attestation_mutuelle",
        [
            "attestation",
            "mutuelle",
            "organisme complementaire",
            "numero adherent",
            r"n[°o]\s*adherent",
            "droits ouverts",
            "date de validite",
            "tiers payant",
            "carte tiers",
        ],
    ),
    (
        "facture",
        [
            "facture",
            r"n[°o]\s*facture",
            "montant ttc",
            "montant ht",
            r"\btva\b",
            "net a payer",
            "reglement",
            "echeance",
        ],
    ),
    (
        "carte_mutuelle",
        [
            "carte mutuelle",
            "carte de tiers payant",
            "organisme",
            r"n[°o]\s*adherent",
            "code organisme",
            "regime obligatoire",
        ],
    ),
]


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
    except Exception as exc:
        logger.warning("pdfplumber_extraction_failed", error=str(exc))

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


def _ocr_pdf_fallback(file_bytes: bytes, page_count_hint: int) -> ExtractedDocument:
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

    for doc_type, keywords in _CLASSIFICATION_RULES:
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
