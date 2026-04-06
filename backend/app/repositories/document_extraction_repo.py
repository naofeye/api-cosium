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


def create(db: Session, **kwargs: object) -> DocumentExtraction:
    extraction = DocumentExtraction(**kwargs)
    db.add(extraction)
    db.commit()
    db.refresh(extraction)
    return extraction


