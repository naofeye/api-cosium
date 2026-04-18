"""Scoring client (0-100) + top clients par CA."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cosium_data import CosiumInvoice


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
            select(func.count())
            .select_from(CosiumInvoice)
            .where(
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
            select(func.count())
            .select_from(ClientMutuelle)
            .where(
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
    pts_outstanding = (
        10 if outstanding == 0 and nb_factures_12m > 0 else (-10 if outstanding > 0 else 0)
    )
    pts_renouvelable = 10 if days_since_last is not None and days_since_last > 730 else 0

    total = max(
        0,
        min(
            100,
            pts_ca + pts_freq + pts_ancien + pts_mutuelle + pts_outstanding + pts_renouvelable,
        ),
    )

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


def get_top_clients_by_ca(
    db: Session, tenant_id: int, limit: int = 10, months: int = 12
) -> list[dict]:
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
        .group_by(
            CosiumInvoice.customer_id,
            CosiumInvoice.customer_name,
            CosiumInvoice.customer_cosium_id,
        )
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
