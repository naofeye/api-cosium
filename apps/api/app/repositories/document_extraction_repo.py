from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document_extraction import DocumentExtraction


def get_by_id(db: Session, extraction_id: int, tenant_id: int) -> DocumentExtraction | None:
    return db.scalars(
        select(DocumentExtraction).where(
            DocumentExtraction.id == extraction_id,
            DocumentExtraction.tenant_id == tenant_id,
        )
    ).first()


def get_by_document_id(db: Session, document_id: int, tenant_id: int) -> DocumentExtraction | None:
    return db.scalars(
        select(DocumentExtraction).where(
            DocumentExtraction.document_id == document_id,
            DocumentExtraction.tenant_id == tenant_id,
        )
    ).first()


def get_by_cosium_document_id(db: Session, cosium_document_id: int, tenant_id: int) -> DocumentExtraction | None:
    return db.scalars(
        select(DocumentExtraction).where(
            DocumentExtraction.cosium_document_id == cosium_document_id,
            DocumentExtraction.tenant_id == tenant_id,
        )
    ).first()


def list_by_customer_cosium_id(
    db: Session, customer_cosium_id: int, tenant_id: int
) -> list[DocumentExtraction]:
    """Return all extractions linked to a customer's Cosium documents."""
    return list(
        db.scalars(
            select(DocumentExtraction).where(
                DocumentExtraction.cosium_document_id == customer_cosium_id,
                DocumentExtraction.tenant_id == tenant_id,
            )
        ).all()
    )


def list_by_customer_cosium_documents(
    db: Session, cosium_document_ids: list[int], tenant_id: int
) -> list[DocumentExtraction]:
    """Return all extractions for a list of Cosium document IDs."""
    if not cosium_document_ids:
        return []
    return list(
        db.scalars(
            select(DocumentExtraction).where(
                DocumentExtraction.cosium_document_id.in_(cosium_document_ids),
                DocumentExtraction.tenant_id == tenant_id,
            )
        ).all()
    )


def create(db: Session, **kwargs: object) -> DocumentExtraction:
    extraction = DocumentExtraction(**kwargs)
    db.add(extraction)
    db.flush()
    db.refresh(extraction)
    return extraction


