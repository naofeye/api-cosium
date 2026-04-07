from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document


def get_by_id(db: Session, document_id: int, tenant_id: int) -> Document | None:
    return db.scalars(select(Document).where(Document.id == document_id, Document.tenant_id == tenant_id)).first()


def list_by_case(db: Session, case_id: int, tenant_id: int, limit: int = 500) -> list[Document]:
    return (
        db.execute(select(Document).where(Document.case_id == case_id, Document.tenant_id == tenant_id).limit(limit))
        .scalars()
        .all()
    )


def create_document(db: Session, tenant_id: int, case_id: int, type: str, filename: str, storage_key: str) -> Document:
    doc = Document(tenant_id=tenant_id, case_id=case_id, type=type, filename=filename, storage_key=storage_key)
    db.add(doc)
    db.flush()
    db.refresh(doc)
    return doc
