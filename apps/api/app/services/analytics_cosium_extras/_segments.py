"""Segments dynamiques + mix produits (suggestions non persistées)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cosium_data import CosiumInvoice


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

    vip_count = (
        db.scalar(
            select(func.count())
            .select_from(ca_per_customer_q)
            .where(ca_per_customer_q.c.ca > 5000)
        )
        or 0
    )
    vip_ca = float(
        db.scalar(select(func.sum(ca_per_customer_q.c.ca)).where(ca_per_customer_q.c.ca > 5000))
        or 0
    )

    renewal_count = (
        db.scalar(
            select(func.count())
            .select_from(ca_per_customer_q)
            .where(
                ca_per_customer_q.c.last_date < cutoff_2y,
                ca_per_customer_q.c.last_date >= now - timedelta(days=1825),
            )
        )
        or 0
    )

    inactive_count = (
        db.scalar(
            select(func.count())
            .select_from(ca_per_customer_q)
            .where(ca_per_customer_q.c.last_date < cutoff_3y)
        )
        or 0
    )

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


def compute_product_mix(db: Session, tenant_id: int, days: int = 90) -> dict:
    """Mix produits sur la periode : CA et quantites par famille.

    Utilise `cosium_invoiced_items` si synchronises. Retourne un fallback vide si table est vide.
    """
    from app.models.cosium_data import CosiumInvoicedItem

    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=days)

    rows = db.execute(
        select(
            CosiumInvoicedItem.product_family,
            func.count().label("nb_lignes"),
            func.coalesce(func.sum(CosiumInvoicedItem.quantity), 0).label("quantite"),
            func.coalesce(func.sum(CosiumInvoicedItem.total_ti), 0).label("ca"),
        )
        .where(
            CosiumInvoicedItem.tenant_id == tenant_id,
            CosiumInvoicedItem.synced_at >= cutoff,
        )
        .group_by(CosiumInvoicedItem.product_family)
        .order_by(func.sum(CosiumInvoicedItem.total_ti).desc())
    ).all()

    families = [
        {
            "family": r.product_family or "non_classe",
            "nb_lignes": int(r.nb_lignes or 0),
            "quantite": int(r.quantite or 0),
            "ca": round(float(r.ca or 0), 2),
        }
        for r in rows
    ]

    ca_total = sum(f["ca"] for f in families)
    for f in families:
        f["share_pct"] = round(f["ca"] / ca_total * 100, 1) if ca_total > 0 else 0.0

    return {
        "period_days": days,
        "synced": len(families) > 0,
        "total_ca": round(ca_total, 2),
        "families": families,
    }
