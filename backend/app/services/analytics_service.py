from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.analytics import (
    AgingBalance,
    AgingBucket,
    CommercialKPIs,
    CosiumKPIs,
    DashboardFull,
    FinancialKPIs,
    MarketingKPIs,
    OperationalKPIs,
    PayerPerf,
    PayerPerformance,
)
from app.models import (
    Campaign,
    Case,
    Devis,
    Document,
    DocumentType,
    Facture,
    MessageLog,
    PayerOrganization,
    Payment,
    PecRequest,
)
from app.models.cosium_data import CosiumInvoice

logger = get_logger("analytics_service")


def get_financial_kpis(
    db: Session, tenant_id: int, date_from: datetime | None = None, date_to: datetime | None = None
) -> FinancialKPIs:
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

    montant_facture = float(db.scalar(q_facture) or 0)
    montant_encaisse = float(db.scalar(q_paid) or 0)
    montant_du = float(db.scalar(q_due) or 0)
    reste = round(montant_du - montant_encaisse, 2)
    taux = round(montant_encaisse / montant_du * 100, 1) if montant_du > 0 else 0

    return FinancialKPIs(
        ca_total=montant_facture,
        montant_facture=montant_facture,
        montant_encaisse=montant_encaisse,
        reste_a_encaisser=max(reste, 0),
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

    buckets_data: dict[str, dict[str, float]] = {
        "0-30j": {"client": 0, "mutuelle": 0, "secu": 0},
        "30-60j": {"client": 0, "mutuelle": 0, "secu": 0},
        "60-90j": {"client": 0, "mutuelle": 0, "secu": 0},
        "90j+": {"client": 0, "mutuelle": 0, "secu": 0},
    }

    for r in rows:
        days = (now - r.created_at).days if r.created_at else 0
        amount = float(r.amount_due) - float(r.amount_paid)
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
    orgs = db.scalars(select(PayerOrganization).where(PayerOrganization.tenant_id == tenant_id)).all()
    payers = []

    for org in orgs:
        pecs = db.execute(
            select(PecRequest.status, PecRequest.montant_demande, PecRequest.montant_accorde).where(
                PecRequest.organization_id == org.id, PecRequest.tenant_id == tenant_id
            )
        ).all()

        total = len(pecs)
        if total == 0:
            continue

        accepted = sum(1 for p in pecs if p.status in ("acceptee", "cloturee") and p.montant_accorde)
        refused = sum(1 for p in pecs if p.status == "refusee")
        total_requested = sum(float(p.montant_demande) for p in pecs)
        total_accepted = sum(float(p.montant_accorde or 0) for p in pecs if p.montant_accorde)

        payers.append(
            PayerPerf(
                name=org.name,
                type=org.type,
                avg_payment_days=0,
                acceptance_rate=round(accepted / total * 100, 1) if total > 0 else 0,
                rejection_rate=round(refused / total * 100, 1) if total > 0 else 0,
                total_requested=round(total_requested, 2),
                total_accepted=round(total_accepted, 2),
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

        # Single GROUP BY query instead of N+1 per-case queries
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

    taux = round(complets / total_cases * 100, 1) if total_cases > 0 else 0

    return OperationalKPIs(
        dossiers_en_cours=total_cases,
        dossiers_complets=complets,
        taux_completude=taux,
        pieces_manquantes=total_missing,
        delai_moyen_jours=0,
    )


def get_commercial_kpis(db: Session, tenant_id: int) -> CommercialKPIs:
    devis_total = db.scalar(select(func.count()).select_from(Devis).where(Devis.tenant_id == tenant_id)) or 0
    devis_brouillon = (
        db.scalar(
            select(func.count())
            .select_from(Devis)
            .where(Devis.tenant_id == tenant_id, Devis.status.in_(["brouillon", "envoye"]))
        )
        or 0
    )
    devis_signes = (
        db.scalar(
            select(func.count())
            .select_from(Devis)
            .where(Devis.tenant_id == tenant_id, Devis.status.in_(["signe", "facture"]))
        )
        or 0
    )
    taux = round(devis_signes / devis_total * 100, 1) if devis_total > 0 else 0

    avg = db.scalar(
        select(func.avg(Devis.montant_ttc)).where(Devis.tenant_id == tenant_id, Devis.status.in_(["signe", "facture"]))
    )
    panier_moyen = round(float(avg), 2) if avg else 0

    # CA par mois (6 derniers mois) — proper month arithmetic
    ca_mois = []
    now = datetime.now(UTC).replace(tzinfo=None)
    for i in range(5, -1, -1):
        # Subtract i months from the current month using proper arithmetic
        target_month = now.month - i
        target_year = now.year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        month_start = datetime(target_year, target_month, 1)
        if i > 0:
            next_month = (month_start + timedelta(days=32)).replace(day=1)
        else:
            next_month = now
        ca = (
            db.scalar(
                select(func.coalesce(func.sum(Facture.montant_ttc), 0))
                .where(Facture.tenant_id == tenant_id)
                .where(Facture.created_at >= month_start, Facture.created_at < next_month)
            )
            or 0
        )
        ca_mois.append(
            {
                "mois": month_start.strftime("%Y-%m"),
                "ca": round(float(ca), 2),
            }
        )

    return CommercialKPIs(
        devis_en_cours=devis_brouillon,
        devis_signes=devis_signes,
        taux_conversion=taux,
        panier_moyen=panier_moyen,
        ca_par_mois=ca_mois,
    )


def get_marketing_kpis(db: Session, tenant_id: int) -> MarketingKPIs:
    total = db.scalar(select(func.count()).select_from(Campaign).where(Campaign.tenant_id == tenant_id)) or 0
    sent = (
        db.scalar(
            select(func.count()).select_from(Campaign).where(Campaign.tenant_id == tenant_id, Campaign.status == "sent")
        )
        or 0
    )
    messages = db.scalar(select(func.count()).select_from(MessageLog).where(MessageLog.tenant_id == tenant_id)) or 0

    return MarketingKPIs(
        campagnes_total=total,
        campagnes_envoyees=sent,
        messages_envoyes=messages,
        taux_ouverture=0,
    )


def get_cosium_kpis(db: Session, tenant_id: int) -> CosiumKPIs:
    """Compute KPIs from real Cosium invoice data."""
    total_facture_cosium = float(
        db.scalar(
            select(func.coalesce(func.sum(CosiumInvoice.total_ti), 0)).where(
                CosiumInvoice.tenant_id == tenant_id, CosiumInvoice.type == "INVOICE"
            )
        )
        or 0
    )
    total_outstanding = float(
        db.scalar(
            select(func.coalesce(func.sum(CosiumInvoice.outstanding_balance), 0)).where(
                CosiumInvoice.tenant_id == tenant_id,
                CosiumInvoice.type == "INVOICE",
                CosiumInvoice.outstanding_balance > 0,
            )
        )
        or 0
    )
    total_paid = round(total_facture_cosium - total_outstanding, 2)

    invoice_count = (
        db.scalar(
            select(func.count())
            .select_from(CosiumInvoice)
            .where(CosiumInvoice.tenant_id == tenant_id, CosiumInvoice.type == "INVOICE")
        )
        or 0
    )
    quote_count = (
        db.scalar(
            select(func.count())
            .select_from(CosiumInvoice)
            .where(CosiumInvoice.tenant_id == tenant_id, CosiumInvoice.type == "QUOTE")
        )
        or 0
    )
    credit_note_count = (
        db.scalar(
            select(func.count())
            .select_from(CosiumInvoice)
            .where(CosiumInvoice.tenant_id == tenant_id, CosiumInvoice.type == "CREDIT_NOTE")
        )
        or 0
    )

    return CosiumKPIs(
        total_facture_cosium=round(total_facture_cosium, 2),
        total_outstanding=round(total_outstanding, 2),
        total_paid=max(total_paid, 0),
        invoice_count=invoice_count,
        quote_count=quote_count,
        credit_note_count=credit_note_count,
    )


def get_dashboard_full(
    db: Session, tenant_id: int, date_from: datetime | None = None, date_to: datetime | None = None
) -> DashboardFull:
    from app.core.redis_cache import cache_get, cache_set

    # Only use cache when no date filters are applied
    cache_key = f"analytics:dashboard:{tenant_id}"
    if not date_from and not date_to:
        cached = cache_get(cache_key)
        if cached:
            logger.debug("dashboard_full_cache_hit", tenant_id=tenant_id)
            return DashboardFull(**cached)

    result = DashboardFull(
        financial=get_financial_kpis(db, tenant_id, date_from, date_to),
        aging=get_aging_balance(db, tenant_id),
        payers=get_payer_performance(db, tenant_id),
        operational=get_operational_kpis(db, tenant_id),
        commercial=get_commercial_kpis(db, tenant_id),
        marketing=get_marketing_kpis(db, tenant_id),
        cosium=get_cosium_kpis(db, tenant_id),
    )

    if not date_from and not date_to:
        cache_set(cache_key, result.model_dump(), ttl=300)

    return result
