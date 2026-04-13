"""DB loaders pour la consolidation PEC.

Charge depuis la base les sources utilisees par consolidation_service :
- Customer (Cosium client lie)
- CosiumPrescription la plus recente
- Devis (par id explicite ou dernier du customer)
- DevisLigne du devis
- ClientMutuelle actives (triees par confiance)
- DocumentExtraction lies au customer (via Case → Document)
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.client import Customer
from app.models.client_mutuelle import ClientMutuelle
from app.models.cosium_data import CosiumPrescription
from app.models.devis import Devis, DevisLigne
from app.models.document_extraction import DocumentExtraction


def load_cosium_client(db: Session, tenant_id: int, customer_id: int) -> Customer | None:
    return db.scalars(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.tenant_id == tenant_id,
        )
    ).first()


def load_latest_prescription(
    db: Session, tenant_id: int, customer_id: int,
) -> CosiumPrescription | None:
    return db.scalars(
        select(CosiumPrescription)
        .where(
            CosiumPrescription.customer_id == customer_id,
            CosiumPrescription.tenant_id == tenant_id,
        )
        .order_by(CosiumPrescription.file_date.desc().nullslast(), CosiumPrescription.id.desc())
        .limit(1)
    ).first()


def load_devis(
    db: Session, tenant_id: int, customer_id: int, devis_id: int | None,
) -> Devis | None:
    """Devis explicite par id, sinon le plus recent du customer."""
    if devis_id:
        return db.scalars(
            select(Devis).where(Devis.id == devis_id, Devis.tenant_id == tenant_id)
        ).first()

    from app.models.case import Case
    return db.scalars(
        select(Devis)
        .join(Case, Case.id == Devis.case_id)
        .where(Case.customer_id == customer_id, Devis.tenant_id == tenant_id)
        .order_by(Devis.created_at.desc())
        .limit(1)
    ).first()


def load_devis_lignes(db: Session, tenant_id: int, devis_id: int) -> list[DevisLigne]:
    return list(
        db.scalars(
            select(DevisLigne).where(
                DevisLigne.devis_id == devis_id,
                DevisLigne.tenant_id == tenant_id,
            )
        ).all()
    )


def load_client_mutuelles(
    db: Session, tenant_id: int, customer_id: int,
) -> list[ClientMutuelle]:
    return list(
        db.scalars(
            select(ClientMutuelle)
            .where(
                ClientMutuelle.customer_id == customer_id,
                ClientMutuelle.tenant_id == tenant_id,
                ClientMutuelle.active.is_(True),
            )
            .order_by(ClientMutuelle.confidence.desc())
        ).all()
    )


def load_document_extractions(
    db: Session, tenant_id: int, customer_id: int,
) -> list[DocumentExtraction]:
    """DocumentExtractions liees aux documents du customer (via Case → Document)."""
    from app.models.case import Case
    from app.models.document import Document

    return list(
        db.scalars(
            select(DocumentExtraction)
            .join(Document, Document.id == DocumentExtraction.document_id)
            .join(Case, Case.id == Document.case_id)
            .where(
                Case.customer_id == customer_id,
                DocumentExtraction.tenant_id == tenant_id,
                DocumentExtraction.structured_data.isnot(None),
            )
            .order_by(DocumentExtraction.created_at.desc())
        ).all()
    )
