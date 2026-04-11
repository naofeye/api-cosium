"""Repository pour les donnees de renouvellement."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Campaign, Case, CosiumPrescription, Customer, Facture, FactureLigne, PecRequest


def get_customers_with_last_purchase(
    db: Session,
    tenant_id: int,
    age_minimum_months: int = 24,
    min_invoice_amount: float = 0.0,
) -> list[dict]:
    """Retourne les clients avec leur derniere facture datant de plus de N mois."""

    cutoff_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=age_minimum_months * 30)

    # Sous-requete : date et montant de la derniere facture par client
    last_facture = (
        select(
            Case.customer_id,
            func.max(Facture.date_emission).label("last_purchase_date"),
            func.max(Facture.montant_ttc).label("last_invoice_amount"),
        )
        .join(Case, Facture.case_id == Case.id)
        .where(
            Facture.tenant_id == tenant_id,
            Facture.status != "annulee",
        )
        .group_by(Case.customer_id)
        .having(func.max(Facture.date_emission) <= cutoff_date)
        .subquery()
    )

    # Joindre avec les clients
    stmt = (
        select(
            Customer,
            last_facture.c.last_purchase_date,
            last_facture.c.last_invoice_amount,
        )
        .join(last_facture, Customer.id == last_facture.c.customer_id)
        .where(Customer.tenant_id == tenant_id)
    )

    if min_invoice_amount > 0:
        stmt = stmt.where(last_facture.c.last_invoice_amount >= min_invoice_amount)

    rows = db.execute(stmt).all()

    results = []
    for customer, last_date, last_amount in rows:
        months_since = int((datetime.now(UTC).replace(tzinfo=None) - last_date).days / 30) if last_date else 0
        results.append(
            {
                "customer": customer,
                "last_purchase_date": last_date,
                "last_invoice_amount": float(last_amount or 0),
                "months_since_purchase": months_since,
            }
        )

    return results


def customer_has_active_pec(db: Session, tenant_id: int, customer_id: int) -> bool:
    """Verifie si le client a une PEC acceptee dans les 12 derniers mois."""
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=365)
    stmt = (
        select(func.count())
        .select_from(PecRequest)
        .join(Case, PecRequest.case_id == Case.id)
        .where(
            PecRequest.tenant_id == tenant_id,
            Case.customer_id == customer_id,
            PecRequest.status == "acceptee",
            PecRequest.created_at >= cutoff,
        )
    )
    return db.execute(stmt).scalar_one() > 0


def get_equipment_type_from_last_invoice(
    db: Session,
    tenant_id: int,
    customer_id: int,
) -> str | None:
    """Determine le type d'equipement de la derniere facture."""
    stmt = (
        select(FactureLigne.designation)
        .join(Facture, FactureLigne.facture_id == Facture.id)
        .join(Case, Facture.case_id == Case.id)
        .where(
            FactureLigne.tenant_id == tenant_id,
            Case.customer_id == customer_id,
        )
        .order_by(Facture.date_emission.desc())
        .limit(1)
    )
    row = db.execute(stmt).scalar_one_or_none()
    if not row:
        return None
    designation = row.lower()
    if any(k in designation for k in ("monture", "lunette")):
        return "monture"
    if any(k in designation for k in ("verre", "progressif", "unifocal")):
        return "verre"
    if any(k in designation for k in ("lentille", "contact")):
        return "lentille"
    if "solaire" in designation:
        return "solaire"
    return "autre"


def get_customers_with_old_prescriptions(
    db: Session,
    tenant_id: int,
    age_minimum_months: int = 24,
) -> list[dict]:
    """Retourne les clients avec une ordonnance datant de plus de N mois (via CosiumPrescription)."""

    cutoff_date = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=age_minimum_months * 30)

    last_prescription = (
        select(
            CosiumPrescription.customer_id,
            func.max(CosiumPrescription.file_date).label("last_prescription_date"),
        )
        .where(
            CosiumPrescription.tenant_id == tenant_id,
            CosiumPrescription.customer_id.isnot(None),
            CosiumPrescription.file_date.isnot(None),
        )
        .group_by(CosiumPrescription.customer_id)
        .having(func.max(CosiumPrescription.file_date) <= cutoff_date)
        .subquery()
    )

    stmt = (
        select(Customer, last_prescription.c.last_prescription_date)
        .join(last_prescription, Customer.id == last_prescription.c.customer_id)
        .where(Customer.tenant_id == tenant_id)
    )

    rows = db.execute(stmt).all()
    results = []
    for customer, last_date in rows:
        months_since = int((datetime.now(UTC).replace(tzinfo=None) - last_date).days / 30) if last_date else 0
        results.append(
            {
                "customer": customer,
                "last_prescription_date": last_date,
                "months_since_prescription": months_since,
            }
        )
    return results


def get_last_prescription_for_customer(
    db: Session,
    tenant_id: int,
    customer_id: int,
) -> CosiumPrescription | None:
    """Retourne la derniere ordonnance d'un client."""
    stmt = (
        select(CosiumPrescription)
        .where(
            CosiumPrescription.tenant_id == tenant_id,
            CosiumPrescription.customer_id == customer_id,
            CosiumPrescription.file_date.isnot(None),
        )
        .order_by(CosiumPrescription.file_date.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def count_renewal_campaigns(db: Session, tenant_id: int, this_month_only: bool = False) -> int:
    """Compte les campagnes de renouvellement."""
    stmt = (
        select(func.count())
        .select_from(Campaign)
        .where(
            Campaign.tenant_id == tenant_id,
            Campaign.name.ilike("%renouvellement%"),
        )
    )
    if this_month_only:
        now = datetime.now(UTC).replace(tzinfo=None)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        stmt = stmt.where(Campaign.created_at >= start_of_month)
    return db.execute(stmt).scalar_one()
