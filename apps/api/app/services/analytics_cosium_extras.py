"""Analytics Cosium extras : score client, top clients, segments, forecast, group comparison.

Decoupage de analytics_cosium_service.py pour respecter la limite de 600 lignes par fichier.
"""
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cosium_data import CosiumInvoice
from app.services.analytics_cosium_service import _aging_bucket_sum


def compute_client_score(db: Session, tenant_id: int, customer_id: int) -> dict:
    """Score client (0-100) base sur historique Cosium + impayes + mutuelle.

    Composantes :
    - CA 12 derniers mois : 0-30 pts (1pt par 100 EUR, plafonne)
    - Frequence achat (nb factures 12 mois) : 0-25 pts
    - Anciennete (annees depuis 1ere facture) : 0-15 pts
    - Mutuelle liee : +10 pts
    - Bonus pas d'impaye : +10 pts ou -10 si impaye
    - Bonus renouvelable (dernier achat > 2 ans) : +10
    """
    from app.models import ClientMutuelle

    cutoff_12m = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=365)
    now = datetime.now(UTC).replace(tzinfo=None)

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

    has_mutuelle = bool(
        db.scalar(
            select(func.count()).select_from(ClientMutuelle).where(
                ClientMutuelle.tenant_id == tenant_id,
                ClientMutuelle.customer_id == customer_id,
            )
        )
        or 0
    )

    pts_ca = min(30, int(ca_12m / 100))
    pts_freq = min(25, nb_factures_12m * 5)
    pts_ancien = min(15, int(years_since_first * 3))
    pts_mutuelle = 10 if has_mutuelle else 0
    pts_outstanding = 10 if outstanding == 0 and nb_factures_12m > 0 else (-10 if outstanding > 0 else 0)
    pts_renouvelable = 10 if days_since_last is not None and days_since_last > 730 else 0

    total = max(0, min(100, pts_ca + pts_freq + pts_ancien + pts_mutuelle + pts_outstanding + pts_renouvelable))

    if total >= 70:
        category, color = "VIP", "emerald"
    elif total >= 40:
        category, color = "Fidele", "blue"
    elif total >= 20:
        category, color = "Standard", "gray"
    else:
        category, color = "Nouveau / Inactif", "amber"

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
    """KPIs comparatifs entre tenants d'un meme groupe (admin reseau)."""
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

    vip_count = db.scalar(
        select(func.count()).select_from(ca_per_customer_q).where(ca_per_customer_q.c.ca > 5000)
    ) or 0
    vip_ca = float(
        db.scalar(
            select(func.sum(ca_per_customer_q.c.ca)).where(ca_per_customer_q.c.ca > 5000)
        ) or 0
    )

    renewal_count = db.scalar(
        select(func.count()).select_from(ca_per_customer_q).where(
            ca_per_customer_q.c.last_date < cutoff_2y,
            ca_per_customer_q.c.last_date >= now - timedelta(days=1825),
        )
    ) or 0

    inactive_count = db.scalar(
        select(func.count()).select_from(ca_per_customer_q).where(
            ca_per_customer_q.c.last_date < cutoff_3y,
        )
    ) or 0

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

    customers_with_mutuelle = (
        db.scalar(
            select(func.count(func.distinct(ClientMutuelle.customer_id))).where(
                ClientMutuelle.tenant_id == tenant_id,
            )
        )
        or 0
    )

    return [
        {"key": "vip", "label": "Clients VIP (CA > 5000 EUR)",
         "description": "Top clients a fideliser. Actions VIP recommandees.",
         "count": vip_count, "ca": round(vip_ca, 2), "color": "emerald"},
        {"key": "renewal_eligible", "label": "Eligibles renouvellement (2-5 ans)",
         "description": "Equipement vieillissant. Cible relance bilan visuel.",
         "count": renewal_count, "color": "purple"},
        {"key": "inactive_3y", "label": "Inactifs > 3 ans",
         "description": "Clients dormants. Reactivation difficile mais utile.",
         "count": inactive_count, "color": "gray"},
        {"key": "with_outstanding", "label": "Avec encours impayes",
         "description": "Clients a relancer pour recouvrement.",
         "count": with_outstanding_count, "color": "red"},
        {"key": "with_mutuelle", "label": "Avec mutuelle configuree",
         "description": "Clients dont la mutuelle OptiFlow est connue.",
         "count": customers_with_mutuelle, "color": "blue"},
    ]


def get_cashflow_forecast(db: Session, tenant_id: int) -> dict:
    """Previsionnel de tresorerie 30j base sur l'age des factures impayees.

    Heuristique : 70%/40%/20%/5% par bucket aging.
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
    irrecoverable_risk = aging_over_90 * 0.95

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
