"""Document extraction orchestration service.

Coordinates OCR extraction, classification, and parsing for documents
stored in MinIO.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.domain.schemas.ocr import DocumentExtractionResponse
from app.integrations.storage import storage
from app.repositories import document_extraction_repo, document_repo
from app.services import ocr_service
from app.services.parsers import parse_document

logger = get_logger("extraction_service")


def extract_document(
    db: Session,
    tenant_id: int,
    document_id: int,
    force: bool = False,
    use_ai: bool = False,
) -> DocumentExtractionResponse:
    """Extract text from a document, classify it, and parse structured data.

    If an extraction already exists and force=False, returns the existing one.
    """
    doc = document_repo.get_by_id(db, document_id=document_id, tenant_id=tenant_id)
    if not doc:
        raise NotFoundError("document", document_id)

    # Check for existing extraction
    if not force:
        existing = document_extraction_repo.get_by_document_id(db, document_id=document_id, tenant_id=tenant_id)
        if existing:
            logger.info("extraction_already_exists", document_id=document_id)
            return DocumentExtractionResponse.model_validate(existing)

    # Download file from MinIO
    try:
        file_bytes = storage.download_file(bucket=settings.s3_bucket, key=doc.storage_key)
    except (ConnectionError, TimeoutError, OSError) as exc:
        logger.error("file_download_failed", document_id=document_id, error=str(exc))
        raise ValidationError("document", f"Impossible de telecharger le fichier: {exc}") from exc

    # Extract text
    extracted, classification = ocr_service.extract_and_classify(file_bytes, doc.filename)

    # Parse structured data (AI-assisted when requested, with regex fallback)
    structured = parse_document(extracted.raw_text, classification.document_type, use_ai=use_ai)
    structured_json = json.dumps(structured, ensure_ascii=False) if structured else None

    # Store extraction result
    extraction = document_extraction_repo.create(
        db,
        tenant_id=tenant_id,
        document_id=document_id,
        raw_text=extracted.raw_text,
        document_type=classification.document_type,
        classification_confidence=classification.confidence,
        extraction_method=extracted.extraction_method,
        ocr_confidence=extracted.confidence,
        structured_data=structured_json,
        extracted_at=datetime.now(UTC),
    )

    logger.info(
        "document_extracted",
        document_id=document_id,
        document_type=classification.document_type,
        extraction_method=extracted.extraction_method,
        text_length=len(extracted.raw_text),
    )

    return DocumentExtractionResponse.model_validate(extraction)


def extract_cosium_document(
    db: Session,
    tenant_id: int,
    cosium_document_id: int,
    force: bool = False,
    use_ai: bool = False,
) -> DocumentExtractionResponse:
    """Extract text from a Cosium document stored in MinIO."""
    from sqlalchemy import select

    from app.models.cosium_data import CosiumDocument

    doc = db.scalars(
        select(CosiumDocument).where(
            CosiumDocument.id == cosium_document_id,
            CosiumDocument.tenant_id == tenant_id,
        )
    ).first()
    if not doc:
        raise NotFoundError("cosium_document", cosium_document_id)

    # Check for existing extraction
    if not force:
        existing = document_extraction_repo.get_by_cosium_document_id(
            db, cosium_document_id=cosium_document_id, tenant_id=tenant_id
        )
        if existing:
            return DocumentExtractionResponse.model_validate(existing)

    # Download from MinIO
    try:
        file_bytes = storage.download_file(bucket="optiflow-docs", key=doc.minio_key)
    except (ConnectionError, TimeoutError, OSError) as exc:
        logger.error("cosium_file_download_failed", cosium_document_id=cosium_document_id, error=str(exc))
        raise ValidationError("cosium_document", f"Impossible de telecharger: {exc}") from exc

    # Extract + classify + parse
    extracted, classification = ocr_service.extract_and_classify(file_bytes, doc.name or "document.pdf")
    structured = parse_document(extracted.raw_text, classification.document_type, use_ai=use_ai)
    structured_json = json.dumps(structured, ensure_ascii=False) if structured else None

    extraction = document_extraction_repo.create(
        db,
        tenant_id=tenant_id,
        cosium_document_id=cosium_document_id,
        raw_text=extracted.raw_text,
        document_type=classification.document_type,
        classification_confidence=classification.confidence,
        extraction_method=extracted.extraction_method,
        ocr_confidence=extracted.confidence,
        structured_data=structured_json,
        extracted_at=datetime.now(UTC),
    )

    logger.info(
        "cosium_document_extracted",
        cosium_document_id=cosium_document_id,
        document_type=classification.document_type,
        text_length=len(extracted.raw_text),
    )

    return DocumentExtractionResponse.model_validate(extraction)
