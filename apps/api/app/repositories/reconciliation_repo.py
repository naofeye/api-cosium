"""Repository for reconciliation data access."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.client import Customer
from app.models.cosium_data import CosiumInvoice, CosiumPayment, CosiumThirdPartyPayment
from app.models.reconciliation import DossierReconciliation


def get_invoices_by_customer(
    db: Session, tenant_id: int, customer_id: int,
    customer_cosium_id: str | None = None,
) -> list[CosiumInvoice]:
    """Get all invoices for a customer by customer_id (preferred) or cosium_id."""
    # Prefer customer_id (82% linked) over customer_cosium_id (0% linked)
    query = db.query(CosiumInvoice).filter(CosiumInvoice.tenant_id == tenant_id)
    query = query.filter(CosiumInvoice.customer_id == customer_id)
    return query.order_by(CosiumInvoice.invoice_date.desc()).all()


def get_payments_by_customer(
    db: Session, tenant_id: int, customer_id: int | None = None,
    customer_cosium_id: str | None = None,
) -> list[CosiumPayment]:
    """Get all payments for a customer by customer_id or customer_cosium_id."""
    q = db.query(CosiumPayment).filter(CosiumPayment.tenant_id == tenant_id)
    if customer_id is not None:
        q = q.filter(CosiumPayment.customer_id == customer_id)
    elif customer_cosium_id is not None:
        q = q.filter(CosiumPayment.customer_cosium_id == customer_cosium_id)
    else:
        return []
    return q.order_by(CosiumPayment.due_date.desc()).all()


def get_third_party_payments_for_invoices(
    db: Session, tenant_id: int, invoice_cosium_ids: list[int],
) -> list[CosiumThirdPartyPayment]:
    """Get third-party payment info for a set of invoices."""
    if not invoice_cosium_ids:
        return []
    return (
        db.query(CosiumThirdPartyPayment)
        .filter(
            CosiumThirdPartyPayment.tenant_id == tenant_id,
            CosiumThirdPartyPayment.invoice_cosium_id.in_(invoice_cosium_ids),
        )
        .all()
    )


def count_payments(db: Session, tenant_id: int) -> int:
    """Count all payments for a tenant."""
    return (
        db.query(func.count(CosiumPayment.id))
        .filter(CosiumPayment.tenant_id == tenant_id)
        .scalar()
    ) or 0


def get_unlinked_payments(db: Session, tenant_id: int) -> list[CosiumPayment]:
    """Get all payments that have no customer_id set."""
    return (
        db.query(CosiumPayment)
        .filter(
            CosiumPayment.tenant_id == tenant_id,
            CosiumPayment.customer_id.is_(None),
        )
        .all()
    )


def get_all_customers(db: Session, tenant_id: int) -> list[Customer]:
    """Get all customers for a tenant."""
    return (
        db.query(Customer)
        .filter(
            Customer.tenant_id == tenant_id,
            Customer.deleted_at.is_(None),
        )
        .all()
    )


def get_customers_with_invoices(db: Session, tenant_id: int) -> list[Customer]:
    """Get customers that have at least one Cosium invoice."""
    customer_cosium_ids = (
        db.query(CosiumInvoice.customer_cosium_id)
        .filter(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.customer_cosium_id.isnot(None),
        )
        .distinct()
        .all()
    )
    ids = [r[0] for r in customer_cosium_ids]
    if not ids:
        return []
    return (
        db.query(Customer)
        .filter(
            Customer.tenant_id == tenant_id,
            Customer.cosium_id.in_(ids),
            Customer.deleted_at.is_(None),
        )
        .all()
    )


def upsert_reconciliation(
    db: Session, tenant_id: int, customer_id: int, data: dict,
) -> DossierReconciliation:
    """Create or update a reconciliation record for a customer."""
    existing = (
        db.query(DossierReconciliation)
        .filter(
            DossierReconciliation.tenant_id == tenant_id,
            DossierReconciliation.customer_id == customer_id,
        )
        .first()
    )
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        db.flush()
        db.refresh(existing)
        return existing

    recon = DossierReconciliation(tenant_id=tenant_id, customer_id=customer_id, **data)
    db.add(recon)
    db.flush()
    db.refresh(recon)
    return recon


def get_reconciliation_by_customer(
    db: Session, tenant_id: int, customer_id: int,
) -> DossierReconciliation | None:
    """Get reconciliation for a specific customer."""
    return (
        db.query(DossierReconciliation)
        .filter(
            DossierReconciliation.tenant_id == tenant_id,
            DossierReconciliation.customer_id == customer_id,
        )
        .first()
    )


def get_reconciliation_summary(
    db: Session, tenant_id: int,
) -> list[tuple]:
    """Get count of reconciliations grouped by status."""
    return (
        db.query(
            DossierReconciliation.status,
            func.count(DossierReconciliation.id),
            func.sum(DossierReconciliation.total_facture),
            func.sum(DossierReconciliation.total_outstanding),
            func.sum(DossierReconciliation.total_paid),
        )
        .filter(DossierReconciliation.tenant_id == tenant_id)
        .group_by(DossierReconciliation.status)
        .all()
    )


def get_reconciliations_by_status(
    db: Session, tenant_id: int, status: str, page: int = 1, page_size: int = 25,
) -> tuple[list[DossierReconciliation], int]:
    """Get paginated reconciliations filtered by status."""
    q = db.query(DossierReconciliation).filter(
        DossierReconciliation.tenant_id == tenant_id,
        DossierReconciliation.status == status,
    )
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return items, total


def get_all_reconciliations(
    db: Session,
    tenant_id: int,
    status: str | None = None,
    confidence: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> tuple[list[tuple], int]:
    """Get paginated reconciliations with customer name, optional filters."""
    q = (
        db.query(DossierReconciliation, Customer)
        .join(Customer, Customer.id == DossierReconciliation.customer_id)
        .filter(
            DossierReconciliation.tenant_id == tenant_id,
            Customer.deleted_at.is_(None),
        )
    )
    if status:
        q = q.filter(DossierReconciliation.status == status)
    if confidence:
        q = q.filter(DossierReconciliation.confidence == confidence)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            (Customer.last_name.ilike(pattern)) | (Customer.first_name.ilike(pattern))
        )
    total = q.count()
    items = (
        q.order_by(DossierReconciliation.total_outstanding.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def get_anomalous_reconciliations(
    db: Session, tenant_id: int, page: int = 1, page_size: int = 25,
) -> tuple[list[DossierReconciliation], int]:
    """Get reconciliations that have anomalies."""
    q = db.query(DossierReconciliation).filter(
        DossierReconciliation.tenant_id == tenant_id,
        DossierReconciliation.anomalies.isnot(None),
        DossierReconciliation.anomalies != "[]",
    )
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return items, total
