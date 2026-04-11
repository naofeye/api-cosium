"""Repository for AI context-building queries (read-only)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Case,
    Customer,
    Devis,
    Document,
    Facture,
    PayerOrganization,
    Payment,
    PecRequest,
)
from app.models.cosium_data import CosiumInvoice, CosiumPayment, CosiumPrescription


def get_case_with_customer(db: Session, case_id: int, tenant_id: int):
    """Return case + customer joined row for context building."""
    return db.execute(
        select(
            Case.id,
            Case.status,
            Case.source,
            Case.created_at,
            Case.customer_id,
            Customer.first_name,
            Customer.last_name,
            Customer.phone,
            Customer.email,
        )
        .join(Customer, Customer.id == Case.customer_id)
        .where(Case.id == case_id, Case.tenant_id == tenant_id)
    ).first()


def get_case_customer_id(db: Session, case_id: int, tenant_id: int) -> int | None:
    """Return the customer_id for a given case."""
    row = db.execute(
        select(Case.customer_id).where(Case.id == case_id, Case.tenant_id == tenant_id)
    ).first()
    return row.customer_id if row else None


def get_case_documents(db: Session, case_id: int):
    """Return documents for a case."""
    return db.execute(
        select(Document.type, Document.filename, Document.uploaded_at)
        .where(Document.case_id == case_id)
    ).all()


def get_case_devis(db: Session, case_id: int):
    """Return devis for a case."""
    return db.execute(
        select(Devis.numero, Devis.status, Devis.montant_ttc, Devis.reste_a_charge)
        .where(Devis.case_id == case_id)
    ).all()


def get_case_factures(db: Session, case_id: int):
    """Return factures for a case."""
    return db.execute(
        select(Facture.numero, Facture.status, Facture.montant_ttc)
        .where(Facture.case_id == case_id)
    ).all()


def get_case_payments(db: Session, case_id: int):
    """Return payments for a case."""
    return db.execute(
        select(Payment.payer_type, Payment.amount_due, Payment.amount_paid, Payment.status)
        .where(Payment.case_id == case_id)
    ).all()


def get_case_pecs(db: Session, case_id: int):
    """Return PEC requests with organization name for a case."""
    return db.execute(
        select(
            PecRequest.id,
            PecRequest.status,
            PecRequest.montant_demande,
            PecRequest.montant_accorde,
            PayerOrganization.name,
        )
        .join(PayerOrganization, PayerOrganization.id == PecRequest.organization_id)
        .where(PecRequest.case_id == case_id)
    ).all()


def get_cosium_invoices(db: Session, customer_id: int, tenant_id: int, limit: int = 20):
    """Return recent Cosium invoices for a customer."""
    return db.execute(
        select(
            CosiumInvoice.invoice_number,
            CosiumInvoice.invoice_date,
            CosiumInvoice.total_ti,
            CosiumInvoice.outstanding_balance,
            CosiumInvoice.type,
            CosiumInvoice.settled,
        )
        .where(
            CosiumInvoice.customer_id == customer_id,
            CosiumInvoice.tenant_id == tenant_id,
        )
        .order_by(CosiumInvoice.invoice_date.desc())
        .limit(limit)
    ).all()


def get_cosium_prescriptions(db: Session, customer_id: int, tenant_id: int, limit: int = 5):
    """Return recent Cosium prescriptions for a customer."""
    return db.execute(
        select(
            CosiumPrescription.prescription_date,
            CosiumPrescription.sphere_right,
            CosiumPrescription.cylinder_right,
            CosiumPrescription.axis_right,
            CosiumPrescription.addition_right,
            CosiumPrescription.sphere_left,
            CosiumPrescription.cylinder_left,
            CosiumPrescription.axis_left,
            CosiumPrescription.addition_left,
            CosiumPrescription.prescriber_name,
        )
        .where(
            CosiumPrescription.customer_id == customer_id,
            CosiumPrescription.tenant_id == tenant_id,
        )
        .order_by(CosiumPrescription.file_date.desc())
        .limit(limit)
    ).all()


def get_cosium_invoice_ids(db: Session, customer_id: int, tenant_id: int) -> list:
    """Return cosium_id list for a customer's invoices."""
    return db.scalars(
        select(CosiumInvoice.cosium_id).where(
            CosiumInvoice.customer_id == customer_id,
            CosiumInvoice.tenant_id == tenant_id,
        )
    ).all()


def get_cosium_payments_by_invoice_ids(db: Session, invoice_ids: list, tenant_id: int, limit: int = 10):
    """Return Cosium payments linked to given invoice IDs."""
    return db.execute(
        select(
            CosiumPayment.amount,
            CosiumPayment.type,
            CosiumPayment.due_date,
            CosiumPayment.payment_number,
        )
        .where(
            CosiumPayment.tenant_id == tenant_id,
            CosiumPayment.invoice_cosium_id.in_(invoice_ids),
        )
        .order_by(CosiumPayment.due_date.desc())
        .limit(limit)
    ).all()


def count_customers(db: Session, tenant_id: int) -> int:
    """Count customers for a tenant."""
    return db.scalar(
        select(func.count()).select_from(Customer).where(Customer.tenant_id == tenant_id)
    ) or 0


def count_cases(db: Session, tenant_id: int) -> int:
    """Count cases for a tenant."""
    return db.scalar(
        select(func.count()).select_from(Case).where(Case.tenant_id == tenant_id)
    ) or 0
