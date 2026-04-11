"""Requetes pour les impayes et PEC en retard (extraction de reminder_repo)."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Case, Customer, PayerOrganization, Payment, PecRequest


def get_overdue_payments(db: Session, tenant_id: int, min_days: int = 7) -> list[dict]:
    rows = db.execute(
        select(
            Payment.id,
            Payment.case_id,
            Payment.facture_id,
            Payment.payer_type,
            Payment.amount_due,
            Payment.amount_paid,
            Payment.created_at,
            Customer.first_name,
            Customer.last_name,
            Customer.email.label("customer_email"),
        )
        .join(Case, Case.id == Payment.case_id)
        .join(Customer, Customer.id == Case.customer_id)
        .where(
            Payment.tenant_id == tenant_id,
            Payment.status.in_(["pending", "partial"]),
            Payment.amount_paid < Payment.amount_due,
        )
        .order_by(Payment.created_at)
    ).all()

    now = datetime.now(UTC).replace(tzinfo=None)
    results = []
    for r in rows:
        days = (now - r.created_at).days if r.created_at else 0
        if days >= min_days:
            results.append(
                {
                    "entity_type": "payment",
                    "entity_id": r.id,
                    "case_id": r.case_id,
                    "facture_id": r.facture_id,
                    "customer_name": f"{r.first_name} {r.last_name}",
                    "customer_email": r.customer_email,
                    "payer_type": r.payer_type,
                    "amount": float(r.amount_due) - float(r.amount_paid),
                    "days_overdue": days,
                }
            )
    return results


def get_overdue_pec(db: Session, tenant_id: int, min_days: int = 7) -> list[dict]:
    rows = db.execute(
        select(
            PecRequest.id,
            PecRequest.case_id,
            PecRequest.organization_id,
            PecRequest.montant_demande,
            PecRequest.montant_accorde,
            PecRequest.status,
            PecRequest.created_at,
            Customer.first_name,
            Customer.last_name,
            PayerOrganization.name.label("org_name"),
            PayerOrganization.contact_email.label("org_email"),
            PayerOrganization.type.label("org_type"),
        )
        .join(Case, Case.id == PecRequest.case_id)
        .join(Customer, Customer.id == Case.customer_id)
        .join(PayerOrganization, PayerOrganization.id == PecRequest.organization_id)
        .where(
            PecRequest.tenant_id == tenant_id,
            PecRequest.status.in_(["soumise", "en_attente"]),
        )
        .order_by(PecRequest.created_at)
    ).all()

    now = datetime.now(UTC).replace(tzinfo=None)
    results = []
    for r in rows:
        days = (now - r.created_at).days if r.created_at else 0
        if days >= min_days:
            results.append(
                {
                    "entity_type": "pec_request",
                    "entity_id": r.id,
                    "case_id": r.case_id,
                    "facture_id": None,
                    "pec_request_id": r.id,
                    "customer_name": f"{r.first_name} {r.last_name}",
                    "customer_email": r.org_email,
                    "payer_type": r.org_type,
                    "org_name": r.org_name,
                    "amount": float(r.montant_demande),
                    "days_overdue": days,
                }
            )
    return results


def get_all_overdue(db: Session, tenant_id: int, min_days: int = 7) -> list[dict]:
    return get_overdue_payments(db, tenant_id, min_days) + get_overdue_pec(db, tenant_id, min_days)
