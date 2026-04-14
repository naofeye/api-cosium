"""Cosium-specific KPI calculations for the analytics dashboard.

Contains KPI functions that query Cosium-synced data (invoices, customers,
calendar events, prescriptions, payments).
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.analytics import (
    CosiumCockpitKPIs,
    CosiumCounts,
    CosiumKPIs,
    CosiumMonthlyCa,
)
from app.models import (
    CosiumCalendarEvent,
    CosiumPayment,
    CosiumPrescription,
    Customer,
)
from app.models.cosium_data import CosiumInvoice

logger = get_logger("analytics_cosium_service")


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

    total_devis_cosium = float(
        db.scalar(
            select(func.coalesce(func.sum(CosiumInvoice.total_ti), 0)).where(
                CosiumInvoice.tenant_id == tenant_id, CosiumInvoice.type == "QUOTE"
            )
        )
        or 0
    )

    total_avoirs_cosium = float(
        db.scalar(
            select(func.coalesce(func.sum(CosiumInvoice.total_ti), 0)).where(
                CosiumInvoice.tenant_id == tenant_id, CosiumInvoice.type == "CREDIT_NOTE"
            )
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
        total_devis_cosium=round(total_devis_cosium, 2),
        total_avoirs_cosium=round(total_avoirs_cosium, 2),
    )


def get_cosium_counts(db: Session, tenant_id: int) -> CosiumCounts:
    """Count key Cosium entities for dashboard summary cards."""
    total_clients = (
        db.scalar(select(func.count()).select_from(Customer).where(Customer.tenant_id == tenant_id)) or 0
    )
    total_rdv = (
        db.scalar(
            select(func.count())
            .select_from(CosiumCalendarEvent)
            .where(CosiumCalendarEvent.tenant_id == tenant_id)
        )
        or 0
    )
    total_prescriptions = (
        db.scalar(
            select(func.count())
            .select_from(CosiumPrescription)
            .where(CosiumPrescription.tenant_id == tenant_id)
        )
        or 0
    )
    total_payments = (
        db.scalar(
            select(func.count())
            .select_from(CosiumPayment)
            .where(CosiumPayment.tenant_id == tenant_id)
        )
        or 0
    )
    return CosiumCounts(
        total_clients=total_clients,
        total_rdv=total_rdv,
        total_prescriptions=total_prescriptions,
        total_payments=total_payments,
    )


def get_cosium_ca_par_mois(db: Session, tenant_id: int) -> list[CosiumMonthlyCa]:
    """Monthly CA from Cosium invoices (last 12 months)."""
    now = datetime.now(UTC).replace(tzinfo=None)
    result: list[CosiumMonthlyCa] = []

    for i in range(11, -1, -1):
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

        ca = float(
            db.scalar(
                select(func.coalesce(func.sum(CosiumInvoice.total_ti), 0))
                .where(CosiumInvoice.tenant_id == tenant_id)
                .where(CosiumInvoice.type == "INVOICE")
                .where(CosiumInvoice.invoice_date >= month_start)
                .where(CosiumInvoice.invoice_date < next_month)
            )
            or 0
        )
        result.append(CosiumMonthlyCa(mois=month_start.strftime("%Y-%m"), ca=round(ca, 2)))

    return result


def _sum_invoices_between(db: Session, tenant_id: int, start: datetime, end: datetime) -> float:
    """Somme des factures (type=INVOICE) sur une plage de dates."""
    return float(
        db.scalar(
            select(func.coalesce(func.sum(CosiumInvoice.total_ti), 0))
            .where(
                CosiumInvoice.tenant_id == tenant_id,
                CosiumInvoice.type == "INVOICE",
                CosiumInvoice.invoice_date >= start,
                CosiumInvoice.invoice_date < end,
            )
        )
        or 0
    )


def _count_invoices_between(db: Session, tenant_id: int, start: datetime, end: datetime) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(CosiumInvoice)
            .where(
                CosiumInvoice.tenant_id == tenant_id,
                CosiumInvoice.type == "INVOICE",
                CosiumInvoice.invoice_date >= start,
                CosiumInvoice.invoice_date < end,
            )
        )
        or 0
    )


def _aging_bucket_sum(db: Session, tenant_id: int, days_min: int, days_max: int | None) -> float:
    """Somme outstanding des factures avec age dans la tranche [days_min, days_max[ jours."""
    now = datetime.now(UTC).replace(tzinfo=None)
    upper_bound = now - timedelta(days=days_min)
    filters = [
        CosiumInvoice.tenant_id == tenant_id,
        CosiumInvoice.type == "INVOICE",
        CosiumInvoice.outstanding_balance > 0,
        CosiumInvoice.invoice_date <= upper_bound,
    ]
    if days_max is not None:
        lower_bound = now - timedelta(days=days_max)
        filters.append(CosiumInvoice.invoice_date > lower_bound)
    return float(
        db.scalar(
            select(func.coalesce(func.sum(CosiumInvoice.outstanding_balance), 0)).where(*filters)
        )
        or 0
    )


def get_financial_breakdown_by_type(
    db: Session, tenant_id: int, date_from: str | None = None, date_to: str | None = None
) -> dict:
    """Ventilation des factures Cosium par type de document (vue comptable).

    Inclut count, total_ti, total_outstanding, share_social_security, share_private_insurance.
    """
    filters = [CosiumInvoice.tenant_id == tenant_id]
    if date_from:
        try:
            filters.append(CosiumInvoice.invoice_date >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            filters.append(CosiumInvoice.invoice_date <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    rows = db.execute(
        select(
            CosiumInvoice.type,
            func.count().label("count"),
            func.coalesce(func.sum(CosiumInvoice.total_ti), 0).label("total_ti"),
            func.coalesce(func.sum(CosiumInvoice.outstanding_balance), 0).label("outstanding"),
            func.coalesce(func.sum(CosiumInvoice.share_social_security), 0).label("ss"),
            func.coalesce(func.sum(CosiumInvoice.share_private_insurance), 0).label("amc"),
        )
        .where(*filters)
        .group_by(CosiumInvoice.type)
        .order_by(func.sum(CosiumInvoice.total_ti).desc())
    ).all()

    breakdown = []
    grand_total = 0.0
    for r in rows:
        ti = float(r.total_ti)
        grand_total += ti
        breakdown.append({
            "type": r.type,
            "count": int(r.count),
            "total_ti": round(ti, 2),
            "outstanding": round(float(r.outstanding), 2),
            "share_social_security": round(float(r.ss), 2),
            "share_private_insurance": round(float(r.amc), 2),
            "share_remaining": round(ti - float(r.ss) - float(r.amc), 2),
        })

    return {
        "breakdown": breakdown,
        "grand_total_ti": round(grand_total, 2),
        "date_from": date_from,
        "date_to": date_to,
    }


def compute_client_score(db: Session, tenant_id: int, customer_id: int) -> dict:
    """Score client (0-100) base sur historique Cosium + impayes + mutuelle.

    Composantes :
    - CA 12 derniers mois : 0-30 pts (1pt par 100 EUR, plafonne)
    - Frequence achat (nb factures 12 mois) : 0-25 pts (5pts par facture, plafonne)
    - Anciennete (annees depuis 1ere facture) : 0-15 pts (3pts par annee, plafonne)
    - Mutuelle liee : +10 pts
    - Bonus pas d'impaye : +10 pts si outstanding=0, sinon penalite -10
    - Bonus jeune client (< 50 ans equipement renouvelable) : +10 si dernier achat > 2 ans
    """
    from app.models import ClientMutuelle

    cutoff_12m = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=365)
    now = datetime.now(UTC).replace(tzinfo=None)

    # CA 12 mois
    ca_12m = float(
        db.scalar(
            select(func.coalesce(func.sum(CosiumInvoice.total_ti), 0)).where(
                CosiumInvoice.tenant_id == tenant_id,
                CosiumInvoice.customer_id == customer_id,
                CosiumInvoice.type == "INVOICE",
                CosiumInvoice.invoice_date >= cutoff_12m,
            )
        )
        or 0
    )
    nb_factures_12m = int(
        db.scalar(
            select(func.count()).select_from(CosiumInvoice).where(
                CosiumInvoice.tenant_id == tenant_id,
                CosiumInvoice.customer_id == customer_id,
                CosiumInvoice.type == "INVOICE",
                CosiumInvoice.invoice_date >= cutoff_12m,
            )
        )
        or 0
    )

    # Anciennete
    first_invoice = db.scalar(
        select(func.min(CosiumInvoice.invoice_date)).where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.customer_id == customer_id,
        )
    )
    last_invoice = db.scalar(
        select(func.max(CosiumInvoice.invoice_date)).where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.customer_id == customer_id,
            CosiumInvoice.type == "INVOICE",
        )
    )
    years_since_first = (now - first_invoice).days / 365 if first_invoice else 0
    days_since_last = (now - last_invoice).days if last_invoice else None

    # Outstanding
    outstanding = float(
        db.scalar(
            select(func.coalesce(func.sum(CosiumInvoice.outstanding_balance), 0)).where(
                CosiumInvoice.tenant_id == tenant_id,
                CosiumInvoice.customer_id == customer_id,
                CosiumInvoice.type == "INVOICE",
                CosiumInvoice.outstanding_balance > 0,
            )
        )
        or 0
    )

    # Mutuelle
    has_mutuelle = bool(
        db.scalar(
            select(func.count()).select_from(ClientMutuelle).where(
                ClientMutuelle.tenant_id == tenant_id,
                ClientMutuelle.customer_id == customer_id,
            )
        )
        or 0
    )

    # Calcul score
    pts_ca = min(30, int(ca_12m / 100))
    pts_freq = min(25, nb_factures_12m * 5)
    pts_ancien = min(15, int(years_since_first * 3))
    pts_mutuelle = 10 if has_mutuelle else 0
    pts_outstanding = 10 if outstanding == 0 and nb_factures_12m > 0 else (-10 if outstanding > 0 else 0)
    pts_renouvelable = 10 if days_since_last is not None and days_since_last > 730 else 0

    total = max(0, min(100, pts_ca + pts_freq + pts_ancien + pts_mutuelle + pts_outstanding + pts_renouvelable))

    if total >= 70:
        category = "VIP"
        color = "emerald"
    elif total >= 40:
        category = "Fidele"
        color = "blue"
    elif total >= 20:
        category = "Standard"
        color = "gray"
    else:
        category = "Nouveau / Inactif"
        color = "amber"

    return {
        "score": total,
        "category": category,
        "color": color,
        "ca_12m": round(ca_12m, 2),
        "nb_factures_12m": nb_factures_12m,
        "years_since_first_invoice": round(years_since_first, 1),
        "days_since_last_invoice": days_since_last,
        "outstanding": round(outstanding, 2),
        "has_mutuelle": has_mutuelle,
        "is_renewable": pts_renouvelable > 0,
        "breakdown": {
            "ca": pts_ca,
            "frequence": pts_freq,
            "anciennete": pts_ancien,
            "mutuelle": pts_mutuelle,
            "outstanding": pts_outstanding,
            "renouvelable": pts_renouvelable,
        },
    }


def compute_group_comparison(db: Session) -> list[dict]:
    """KPIs comparatifs entre tenants d'un meme groupe (admin reseau).

    Calcule pour chaque tenant : CA 30j, panier moyen, encours, nb factures,
    nb clients actifs.
    """
    from app.models import Customer, Tenant
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30)

    tenants = db.scalars(select(Tenant).where(Tenant.is_active.is_(True))).all()
    result = []
    for t in tenants:
        ca_30d = float(
            db.scalar(
                select(func.coalesce(func.sum(CosiumInvoice.total_ti), 0)).where(
                    CosiumInvoice.tenant_id == t.id,
                    CosiumInvoice.type == "INVOICE",
                    CosiumInvoice.invoice_date >= cutoff,
                )
            )
            or 0
        )
        nb = int(
            db.scalar(
                select(func.count()).select_from(CosiumInvoice).where(
                    CosiumInvoice.tenant_id == t.id,
                    CosiumInvoice.type == "INVOICE",
                    CosiumInvoice.invoice_date >= cutoff,
                )
            )
            or 0
        )
        outstanding = float(
            db.scalar(
                select(func.coalesce(func.sum(CosiumInvoice.outstanding_balance), 0)).where(
                    CosiumInvoice.tenant_id == t.id,
                    CosiumInvoice.type == "INVOICE",
                    CosiumInvoice.outstanding_balance > 0,
                )
            )
            or 0
        )
        nb_clients = int(
            db.scalar(
                select(func.count()).select_from(Customer).where(Customer.tenant_id == t.id)
            )
            or 0
        )
        result.append({
            "tenant_id": t.id,
            "tenant_name": t.name,
            "tenant_slug": t.slug,
            "ca_30d": round(ca_30d, 2),
            "nb_invoices_30d": nb,
            "panier_moyen": round(ca_30d / nb, 2) if nb > 0 else 0,
            "outstanding_total": round(outstanding, 2),
            "nb_customers": nb_clients,
        })
    return sorted(result, key=lambda r: r["ca_30d"], reverse=True)


def compute_dynamic_segments(db: Session, tenant_id: int) -> list[dict]:
    """Segments marketing dynamiques calcules sur Cosium data (suggestions, non persistes)."""
    from app.models import ClientMutuelle

    now = datetime.now(UTC).replace(tzinfo=None)
    cutoff_2y = now - timedelta(days=730)
    cutoff_3y = now - timedelta(days=1095)

    # Clients avec total CA INVOICE par customer_id
    ca_per_customer_q = (
        select(
            CosiumInvoice.customer_id,
            func.sum(CosiumInvoice.total_ti).label("ca"),
            func.max(CosiumInvoice.invoice_date).label("last_date"),
        )
        .where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.type == "INVOICE",
            CosiumInvoice.customer_id.isnot(None),
        )
        .group_by(CosiumInvoice.customer_id)
        .subquery()
    )

    # VIP : CA > 5000€
    vip_count = db.scalar(
        select(func.count()).select_from(ca_per_customer_q).where(ca_per_customer_q.c.ca > 5000)
    ) or 0
    vip_ca = float(
        db.scalar(
            select(func.sum(ca_per_customer_q.c.ca)).where(ca_per_customer_q.c.ca > 5000)
        ) or 0
    )

    # Renouvellement eligible : dernier achat 2-5 ans
    renewal_count = db.scalar(
        select(func.count()).select_from(ca_per_customer_q).where(
            ca_per_customer_q.c.last_date < cutoff_2y,
            ca_per_customer_q.c.last_date >= now - timedelta(days=1825),
        )
    ) or 0

    # Inactif > 3 ans
    inactive_count = db.scalar(
        select(func.count()).select_from(ca_per_customer_q).where(
            ca_per_customer_q.c.last_date < cutoff_3y,
        )
    ) or 0

    # Avec impayes
    with_outstanding_count = (
        db.scalar(
            select(func.count(func.distinct(CosiumInvoice.customer_id))).where(
                CosiumInvoice.tenant_id == tenant_id,
                CosiumInvoice.type == "INVOICE",
                CosiumInvoice.outstanding_balance > 0,
                CosiumInvoice.customer_id.isnot(None),
            )
        )
        or 0
    )

    # Sans mutuelle
    customers_with_mutuelle = (
        db.scalar(
            select(func.count(func.distinct(ClientMutuelle.customer_id))).where(
                ClientMutuelle.tenant_id == tenant_id,
            )
        )
        or 0
    )

    return [
        {
            "key": "vip",
            "label": "Clients VIP (CA > 5000 EUR)",
            "description": "Top clients a fideliser. Actions VIP recommandees.",
            "count": vip_count,
            "ca": round(vip_ca, 2),
            "color": "emerald",
        },
        {
            "key": "renewal_eligible",
            "label": "Eligibles renouvellement (2-5 ans)",
            "description": "Equipement vieillissant. Cible relance bilan visuel.",
            "count": renewal_count,
            "color": "purple",
        },
        {
            "key": "inactive_3y",
            "label": "Inactifs > 3 ans",
            "description": "Clients dormants. Reactivation difficile mais utile.",
            "count": inactive_count,
            "color": "gray",
        },
        {
            "key": "with_outstanding",
            "label": "Avec encours impayes",
            "description": "Clients a relancer pour recouvrement.",
            "count": with_outstanding_count,
            "color": "red",
        },
        {
            "key": "with_mutuelle",
            "label": "Avec mutuelle configuree",
            "description": "Clients dont la mutuelle OptiFlow est connue.",
            "count": customers_with_mutuelle,
            "color": "blue",
        },
    ]


def get_cashflow_forecast(db: Session, tenant_id: int) -> dict:
    """Previsionnel de tresorerie 30j base sur l'age des factures impayees.

    Heuristique :
    - 0-30j : 70% chance d'encaissement dans les 30 prochains jours
    - 30-60j : 40% chance
    - 60-90j : 20% chance
    - 90j+ : 5% chance (irrecouvrable potentiel)
    """
    aging_0_30 = _aging_bucket_sum(db, tenant_id, 0, 30)
    aging_30_60 = _aging_bucket_sum(db, tenant_id, 30, 60)
    aging_60_90 = _aging_bucket_sum(db, tenant_id, 60, 90)
    aging_over_90 = _aging_bucket_sum(db, tenant_id, 90, None)

    expected_30d = (
        aging_0_30 * 0.70
        + aging_30_60 * 0.40
        + aging_60_90 * 0.20
        + aging_over_90 * 0.05
    )
    irrecoverable_risk = aging_over_90 * 0.95  # part probablement perdue

    return {
        "outstanding_total": round(aging_0_30 + aging_30_60 + aging_60_90 + aging_over_90, 2),
        "expected_30d": round(expected_30d, 2),
        "irrecoverable_risk": round(irrecoverable_risk, 2),
        "buckets": {
            "0_30": round(aging_0_30, 2),
            "30_60": round(aging_30_60, 2),
            "60_90": round(aging_60_90, 2),
            "over_90": round(aging_over_90, 2),
        },
    }


def get_top_clients_by_ca(db: Session, tenant_id: int, limit: int = 10, months: int = 12) -> list[dict]:
    """Top N clients par CA sur les N derniers mois (factures Cosium INVOICE)."""
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=months * 30)

    rows = db.execute(
        select(
            CosiumInvoice.customer_id,
            CosiumInvoice.customer_name,
            CosiumInvoice.customer_cosium_id,
            func.coalesce(func.sum(CosiumInvoice.total_ti), 0).label("ca"),
            func.count(CosiumInvoice.id).label("nb_invoices"),
            func.max(CosiumInvoice.invoice_date).label("last_invoice"),
            func.coalesce(func.sum(CosiumInvoice.outstanding_balance), 0).label("outstanding"),
        )
        .where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.type == "INVOICE",
            CosiumInvoice.invoice_date >= cutoff,
        )
        .group_by(CosiumInvoice.customer_id, CosiumInvoice.customer_name, CosiumInvoice.customer_cosium_id)
        .order_by(func.sum(CosiumInvoice.total_ti).desc())
        .limit(limit)
    ).all()

    return [
        {
            "customer_id": r.customer_id,
            "customer_name": r.customer_name or "Client inconnu",
            "customer_cosium_id": r.customer_cosium_id,
            "ca": round(float(r.ca), 2),
            "nb_invoices": int(r.nb_invoices),
            "last_invoice_date": r.last_invoice.isoformat() if r.last_invoice else None,
            "outstanding": round(float(r.outstanding), 2),
        }
        for r in rows
    ]


def get_cosium_cockpit_kpis(db: Session, tenant_id: int) -> CosiumCockpitKPIs:
    """KPIs cockpit opticien : CA jour/semaine/mois, panier moyen, taux transformation, balance agee."""
    now = datetime.now(UTC).replace(tzinfo=None)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)
    week_start = today_start - timedelta(days=today_start.weekday())  # Monday
    month_start = today_start.replace(day=1)
    last_month_end = month_start
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    same_month_last_year_start = month_start.replace(year=month_start.year - 1)
    same_month_last_year_end = (same_month_last_year_start + timedelta(days=32)).replace(day=1)

    ca_today = _sum_invoices_between(db, tenant_id, today_start, tomorrow_start)
    ca_week = _sum_invoices_between(db, tenant_id, week_start, tomorrow_start)
    ca_month = _sum_invoices_between(db, tenant_id, month_start, tomorrow_start)
    ca_last_month = _sum_invoices_between(db, tenant_id, last_month_start, last_month_end)
    ca_same_month_last_year = _sum_invoices_between(
        db, tenant_id, same_month_last_year_start, same_month_last_year_end
    )

    nb_today = _count_invoices_between(db, tenant_id, today_start, tomorrow_start)
    nb_month = _count_invoices_between(db, tenant_id, month_start, tomorrow_start)
    panier_moyen = round(ca_month / nb_month, 2) if nb_month > 0 else 0.0

    # Taux transformation : invoices / quotes (sur les 90 derniers jours)
    cutoff = now - timedelta(days=90)
    nb_quotes = (
        db.scalar(
            select(func.count())
            .select_from(CosiumInvoice)
            .where(
                CosiumInvoice.tenant_id == tenant_id,
                CosiumInvoice.type == "QUOTE",
                CosiumInvoice.invoice_date >= cutoff,
            )
        )
        or 0
    )
    nb_invoices_recent = _count_invoices_between(db, tenant_id, cutoff, tomorrow_start)
    quote_to_invoice_rate = round((nb_invoices_recent / nb_quotes) * 100, 1) if nb_quotes > 0 else 0.0

    # Balance agee
    aging_0_30 = _aging_bucket_sum(db, tenant_id, 0, 30)
    aging_30_60 = _aging_bucket_sum(db, tenant_id, 30, 60)
    aging_60_90 = _aging_bucket_sum(db, tenant_id, 60, 90)
    aging_over_90 = _aging_bucket_sum(db, tenant_id, 90, None)

    # Ventes latentes : devis non transformes (90 derniers jours, outstanding=0 = non factures)
    latent_cutoff = now - timedelta(days=90)
    latent_row = db.execute(
        select(
            func.count().label("nb"),
            func.coalesce(func.sum(CosiumInvoice.total_ti), 0).label("amount"),
        )
        .where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.type == "QUOTE",
            CosiumInvoice.invoice_date >= latent_cutoff,
            CosiumInvoice.outstanding_balance == 0,  # heuristique non transforme
        )
    ).first()

    return CosiumCockpitKPIs(
        ca_today=round(ca_today, 2),
        ca_this_week=round(ca_week, 2),
        ca_this_month=round(ca_month, 2),
        ca_last_month=round(ca_last_month, 2),
        ca_same_month_last_year=round(ca_same_month_last_year, 2),
        panier_moyen=panier_moyen,
        nb_invoices_today=nb_today,
        nb_invoices_this_month=nb_month,
        quote_to_invoice_rate=quote_to_invoice_rate,
        aging_0_30=round(aging_0_30, 2),
        aging_30_60=round(aging_30_60, 2),
        aging_60_90=round(aging_60_90, 2),
        aging_over_90=round(aging_over_90, 2),
        aging_total=round(aging_0_30 + aging_30_60 + aging_60_90 + aging_over_90, 2),
        latent_quotes_count=int(latent_row.nb) if latent_row else 0,
        latent_quotes_amount=round(float(latent_row.amount), 2) if latent_row else 0,
    )
