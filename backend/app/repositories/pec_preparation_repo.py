"""Repository for PEC preparations and their linked documents."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.pec_preparation import PecPreparation, PecPreparationDocument

# --- PecPreparation ---


def create(
    db: Session,
    tenant_id: int,
    customer_id: int,
    devis_id: int | None = None,
    consolidated_data: str | None = None,
    status: str = "en_preparation",
    completude_score: float = 0.0,
    errors_count: int = 0,
    warnings_count: int = 0,
    user_validations: str | None = None,
    user_corrections: str | None = None,
    created_by: int | None = None,
) -> PecPreparation:
    prep = PecPreparation(
        tenant_id=tenant_id,
        customer_id=customer_id,
        devis_id=devis_id,
        consolidated_data=consolidated_data,
        status=status,
        completude_score=completude_score,
        errors_count=errors_count,
        warnings_count=warnings_count,
        user_validations=user_validations,
        user_corrections=user_corrections,
        created_by=created_by,
    )
    db.add(prep)
    db.commit()
    db.refresh(prep)
    return prep


def get_by_id(
    db: Session, preparation_id: int, tenant_id: int
) -> PecPreparation | None:
    return db.scalars(
        select(PecPreparation).where(
            PecPreparation.id == preparation_id,
            PecPreparation.tenant_id == tenant_id,
        )
    ).first()


def list_by_customer(
    db: Session, customer_id: int, tenant_id: int, limit: int = 25, offset: int = 0
) -> list[PecPreparation]:
    return list(
        db.scalars(
            select(PecPreparation)
            .where(
                PecPreparation.customer_id == customer_id,
                PecPreparation.tenant_id == tenant_id,
            )
            .order_by(PecPreparation.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )


def list_all(
    db: Session,
    tenant_id: int,
    status: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> list[PecPreparation]:
    """List all PEC preparations for a tenant with optional status filter."""
    stmt = (
        select(PecPreparation)
        .where(PecPreparation.tenant_id == tenant_id)
    )
    if status:
        stmt = stmt.where(PecPreparation.status == status)
    stmt = stmt.order_by(PecPreparation.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


def count_all(
    db: Session,
    tenant_id: int,
    status: str | None = None,
) -> int:
    """Count all PEC preparations for a tenant with optional status filter."""
    from sqlalchemy import func

    stmt = select(func.count()).select_from(PecPreparation).where(
        PecPreparation.tenant_id == tenant_id
    )
    if status:
        stmt = stmt.where(PecPreparation.status == status)
    return db.scalar(stmt) or 0


def count_by_status(db: Session, tenant_id: int) -> dict[str, int]:
    """Count preparations by status for a tenant."""
    from sqlalchemy import func

    rows = db.execute(
        select(PecPreparation.status, func.count())
        .where(PecPreparation.tenant_id == tenant_id)
        .group_by(PecPreparation.status)
    ).all()
    return {row[0]: row[1] for row in rows}


def update(db: Session, prep: PecPreparation, **kwargs: object) -> PecPreparation:
    for key, value in kwargs.items():
        if hasattr(prep, key):
            setattr(prep, key, value)
    db.commit()
    db.refresh(prep)
    return prep


def delete(db: Session, prep: PecPreparation) -> None:
    db.delete(prep)
    db.commit()


# --- PecPreparationDocument ---


def add_document(
    db: Session,
    preparation_id: int,
    document_id: int | None = None,
    cosium_document_id: int | None = None,
    document_role: str = "autre",
    extraction_id: int | None = None,
) -> PecPreparationDocument:
    doc = PecPreparationDocument(
        preparation_id=preparation_id,
        document_id=document_id,
        cosium_document_id=cosium_document_id,
        document_role=document_role,
        extraction_id=extraction_id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def list_documents(
    db: Session, preparation_id: int
) -> list[PecPreparationDocument]:
    return list(
        db.scalars(
            select(PecPreparationDocument).where(
                PecPreparationDocument.preparation_id == preparation_id,
            )
        ).all()
    )


