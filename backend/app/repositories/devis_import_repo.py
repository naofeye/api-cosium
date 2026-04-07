"""Repository for devis import operations from Cosium quotes."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.case import Case
from app.models.cosium_data import CosiumInvoice
from app.models.devis import Devis, DevisLigne


def get_quotes(
    db: Session,
    tenant_id: int,
    customer_id: int | None = None,
) -> list[CosiumInvoice]:
    """Return all QUOTE-type Cosium invoices, optionally filtered by customer."""
    stmt = (
        select(CosiumInvoice)
        .where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.type == "QUOTE",
        )
        .order_by(CosiumInvoice.invoice_date.desc())
    )
    if customer_id is not None:
        stmt = stmt.where(CosiumInvoice.customer_id == customer_id)
    return list(db.scalars(stmt).all())


def devis_exists_by_numero(db: Session, tenant_id: int, numero: str) -> bool:
    """Check if a devis with this numero already exists."""
    return db.scalar(
        select(Devis.id)
        .where(Devis.tenant_id == tenant_id, Devis.numero == numero)
        .limit(1)
    ) is not None


def find_latest_case(db: Session, tenant_id: int, customer_id: int) -> Case | None:
    """Find the most recent active case for a customer."""
    return db.scalars(
        select(Case)
        .where(
            Case.customer_id == customer_id,
            Case.tenant_id == tenant_id,
            Case.deleted_at.is_(None),
        )
        .order_by(Case.created_at.desc())
        .limit(1)
    ).first()


def create_case(db: Session, tenant_id: int, customer_id: int) -> Case:
    """Create a new case for Cosium import."""
    case = Case(
        tenant_id=tenant_id,
        customer_id=customer_id,
        status="complet",
        source="cosium",
    )
    db.add(case)
    db.flush()
    return case


def create_devis(db: Session, **kwargs) -> Devis:
    """Create a Devis record."""
    devis = Devis(**kwargs)
    db.add(devis)
    db.flush()
    return devis


def create_devis_ligne(db: Session, **kwargs) -> DevisLigne:
    """Create a DevisLigne record."""
    ligne = DevisLigne(**kwargs)
    db.add(ligne)
    return ligne
