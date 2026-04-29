"""KPI calculation functions for the analytics dashboard.

Contains individual KPI computation functions: financial, aging balance,
payer performance, operational, commercial, marketing.
Cosium-specific KPIs are in analytics_cosium_service.py (re-exported here).
Commercial and marketing KPI helpers are in analytics_kpi_helpers.py (re-exported here).
"""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import PEC_ACCEPTEE, PEC_CLOTUREE, PEC_REFUSEE
from app.core.logging import get_logger
from app.domain.schemas.analytics import (
    AgingBalance,
    AgingBucket,
    FinancialKPIs,
    OperationalKPIs,
    PayerPerf,
    PayerPerformance,
)
from app.models import (
    Case,
    Document,
    DocumentType,
    Facture,
    PayerOrganization,
    Payment,
    PecRequest,
)
from app.models.cosium_data import CosiumInvoice

# Re-export Cosium KPI functions for backward compatibility
from app.services.analytics_cosium_service import (  # noqa: F401
    get_cosium_ca_par_mois,
    get_cosium_counts,
    get_cosium_kpis,
)

# Re-export commercial/marketing KPI helpers for backward compatibility
from app.services.analytics_kpi_helpers import (  # noqa: F401
    get_commercial_kpis,
    get_marketing_kpis,
)

logger = get_logger("analytics_kpi_service")


def get_financial_kpis(
    db: Session, tenant_id: int, date_from: datetime | None = None, date_to: datetime | None = None
) -> FinancialKPIs:
    # --- OptiFlow internal data ---
    q_facture = select(func.coalesce(func.sum(Facture.montant_ttc), 0)).where(Facture.tenant_id == tenant_id)
    q_paid = select(func.coalesce(func.sum(Payment.amount_paid), 0)).where(Payment.tenant_id == tenant_id)
    q_due = select(func.coalesce(func.sum(Payment.amount_due), 0)).where(Payment.tenant_id == tenant_id)

    if date_from:
        q_facture = q_facture.where(Facture.created_at >= date_from)
        q_paid = q_paid.where(Payment.created_at >= date_from)
        q_due = q_due.where(Payment.created_at >= date_from)
    if date_to:
        q_facture = q_facture.where(Facture.created_at <= date_to)
        q_paid = q_paid.where(Payment.created_at <= date_to)
        q_due = q_due.where(Payment.created_at <= date_to)

    of_montant_facture = Decimal(str(db.scalar(q_facture) or 0))
    of_montant_encaisse = Decimal(str(db.scalar(q_paid) or 0))
    of_montant_du = Decimal(str(db.scalar(q_due) or 0))

    # --- Cosium data (real ERP data) ---
    q_cosium_ca = select(func.coalesce(func.sum(CosiumInvoice.total_ti), 0)).where(
        CosiumInvoice.tenant_id == tenant_id, CosiumInvoice.type == "INVOICE"
    )
    q_cosium_outstanding = select(func.coalesce(func.sum(CosiumInvoice.outstanding_balance), 0)).where(
        CosiumInvoice.tenant_id == tenant_id,
        CosiumInvoice.type == "INVOICE",
        CosiumInvoice.outstanding_balance > 0,
    )
    if date_from:
        q_cosium_ca = q_cosium_ca.where(CosiumInvoice.invoice_date >= date_from)
        q_cosium_outstanding = q_cosium_outstanding.where(CosiumInvoice.invoice_date >= date_from)
    if date_to:
        q_cosium_ca = q_cosium_ca.where(CosiumInvoice.invoice_date <= date_to)
        q_cosium_outstanding = q_cosium_outstanding.where(CosiumInvoice.invoice_date <= date_to)

    cosium_ca = Decimal(str(db.scalar(q_cosium_ca) or 0))
    cosium_outstanding = Decimal(str(db.scalar(q_cosium_outstanding) or 0))
    cosium_paid = round(cosium_ca - cosium_outstanding, 2)

    cosium_payments_synced = not (cosium_ca > 0 and cosium_outstanding >= cosium_ca)

    if cosium_ca > 0 and cosium_payments_synced:
        ca_total = round(cosium_ca, 2)
        montant_encaisse = round(max(cosium_paid, 0), 2)
        reste_a_encaisser = round(cosium_outstanding, 2)
    else:
        ca_total = of_montant_facture
        montant_encaisse = of_montant_encaisse
        reste_du = round(of_montant_du - of_montant_encaisse, 2)
        reste_a_encaisser = max(reste_du, 0)

    taux = round(montant_encaisse / ca_total * 100, 1) if ca_total > 0 else 0

    return FinancialKPIs(
        ca_total=ca_total,
        montant_facture=ca_total,
        montant_encaisse=montant_encaisse,
        reste_a_encaisser=reste_a_encaisser,
        taux_recouvrement=taux,
    )


def get_aging_balance(db: Session, tenant_id: int) -> AgingBalance:
    now = datetime.now(UTC).replace(tzinfo=None)
    rows = db.execute(
        select(
            Payment.payer_type,
            Payment.amount_due,
            Payment.amount_paid,
            Payment.created_at,
        )
        .where(Payment.tenant_id == tenant_id)
        .where(Payment.status.in_(["pending", "partial"]))
        .where(Payment.amount_paid < Payment.amount_due)
    ).all()

    zero = Decimal("0")
    buckets_data: dict[str, dict[str, Decimal]] = {
        "0-30j": {"client": zero, "mutuelle": zero, "secu": zero},
        "30-60j": {"client": zero, "mutuelle": zero, "secu": zero},
        "60-90j": {"client": zero, "mutuelle": zero, "secu": zero},
        "90j+": {"client": zero, "mutuelle": zero, "secu": zero},
    }

    for r in rows:
        days = (now - r.created_at).days if r.created_at else 0
        amount = Decimal(str(r.amount_due)) - Decimal(str(r.amount_paid))
        payer = r.payer_type if r.payer_type in ("client", "mutuelle", "secu") else "client"

        if days < 30:
            buckets_data["0-30j"][payer] += amount
        elif days < 60:
            buckets_data["30-60j"][payer] += amount
        elif days < 90:
            buckets_data["60-90j"][payer] += amount
        else:
            buckets_data["90j+"][payer] += amount

    buckets = []
    total = 0
    for tranche, data in buckets_data.items():
        t = round(sum(data.values()), 2)
        total += t
        buckets.append(
            AgingBucket(
                tranche=tranche,
                client=round(data["client"], 2),
                mutuelle=round(data["mutuelle"], 2),
                secu=round(data["secu"], 2),
                total=t,
            )
        )

    return AgingBalance(buckets=buckets, total=round(total, 2))


def get_payer_performance(db: Session, tenant_id: int) -> PayerPerformance:
    """KPIs de performance par organisme payeur (mutuelle, CPAM, etc.).

    Optimisation N+1 : 1 seule query qui agregge les PEC par organization_id
    via GROUP BY. Avant : 1 query par PayerOrganization, soit 50+ round-trips.
    """
    orgs = db.scalars(
        select(PayerOrganization).where(PayerOrganization.tenant_id == tenant_id)
    ).all()
    if not orgs:
        return PayerPerformance(payers=[])

    org_by_id = {org.id: org for org in orgs}

    # Une seule query : on charge toutes les PEC de tous les organismes du tenant
    rows = db.execute(
        select(
            PecRequest.organization_id,
            PecRequest.status,
            PecRequest.montant_demande,
            PecRequest.montant_accorde,
        ).where(PecRequest.tenant_id == tenant_id)
    ).all()

    # Agreggation en Python (groupBy organization_id)
    by_org: dict[int, dict] = {}
    for org_id, status, demande, accorde in rows:
        if org_id not in org_by_id:
            continue  # PEC sur organisme d'un autre tenant (defense en profondeur)
        bucket = by_org.setdefault(
            org_id,
            {"total": 0, "accepted": 0, "refused": 0, "requested": Decimal("0"), "got": Decimal("0")},
        )
        bucket["total"] += 1
        if status in (PEC_ACCEPTEE, PEC_CLOTUREE) and accorde:
            bucket["accepted"] += 1
        if status == PEC_REFUSEE:
            bucket["refused"] += 1
        bucket["requested"] += Decimal(str(demande))
        if accorde:
            bucket["got"] += Decimal(str(accorde))

    payers = []
    for org_id, b in by_org.items():
        org = org_by_id[org_id]
        total = b["total"]
        if total == 0:
            continue
        payers.append(
            PayerPerf(
                name=org.name,
                type=org.type,
                avg_payment_days=0,
                acceptance_rate=round(b["accepted"] / total * 100, 1),
                rejection_rate=round(b["refused"] / total * 100, 1),
                total_requested=round(b["requested"], 2),
                total_accepted=round(b["got"], 2),
            )
        )

    return PayerPerformance(payers=payers)


def get_operational_kpis(db: Session, tenant_id: int) -> OperationalKPIs:
    total_cases = db.scalar(select(func.count()).select_from(Case).where(Case.tenant_id == tenant_id)) or 0

    required_count = (
        db.scalar(select(func.count()).select_from(DocumentType).where(DocumentType.is_required.is_(True))) or 0
    )

    complets = 0
    total_missing = 0

    if required_count > 0:
        required_codes = [
            c for (c,) in db.execute(select(DocumentType.code).where(DocumentType.is_required.is_(True))).all()
        ]
        cases = db.scalars(select(Case.id).where(Case.tenant_id == tenant_id)).all()

        case_doc_counts = dict(
            db.execute(
                select(Document.case_id, func.count(func.distinct(Document.type)))
                .where(Document.tenant_id == tenant_id, Document.type.in_(required_codes))
                .group_by(Document.case_id)
            ).all()
        )

        for case_id in cases:
            present = case_doc_counts.get(case_id, 0)
            missing = required_count - present
            total_missing += missing
            if missing == 0:
                complets += 1
    else:
        # No required document types: all cases are considered complete
        complets = total_cases

    taux = round(complets / total_cases * 100, 1) if total_cases > 0 else 0

    return OperationalKPIs(
        dossiers_en_cours=total_cases,
        dossiers_complets=complets,
        taux_completude=taux,
        pieces_manquantes=total_missing,
        delai_moyen_jours=0,
    )



