"""Comparaisons inter-tenants (groupe) + patterns temporels (heures de contact)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cosium_data import CosiumInvoice
from app.models.interaction import Interaction


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
                select(func.count())
                .select_from(CosiumInvoice)
                .where(
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
                select(func.count())
                .select_from(Customer)
                .where(Customer.tenant_id == t.id)
            )
            or 0
        )
        result.append(
            {
                "tenant_id": t.id,
                "tenant_name": t.name,
                "tenant_slug": t.slug,
                "ca_30d": round(ca_30d, 2),
                "nb_invoices_30d": nb,
                "panier_moyen": round(ca_30d / nb, 2) if nb > 0 else 0,
                "outstanding_total": round(outstanding, 2),
                "nb_customers": nb_clients,
            }
        )
    return sorted(result, key=lambda r: r["ca_30d"], reverse=True)


def compute_best_contact_hour(db: Session, tenant_id: int, min_sample: int = 10) -> dict:
    """Retourne l'heure moyenne conseillee pour contacter les clients.

    Heuristique : regarde les interactions entrantes (reponses clients) des 6 derniers mois,
    groupe par heure, renvoie les 3 tranches horaires les plus actives.
    """
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=180)

    rows = db.execute(
        select(
            func.extract("hour", Interaction.created_at).label("hour"),
            func.count().label("count"),
        )
        .where(
            Interaction.tenant_id == tenant_id,
            Interaction.direction == "entrant",
            Interaction.created_at >= cutoff,
        )
        .group_by("hour")
        .order_by(func.count().desc())
    ).all()

    total = sum(int(r.count) for r in rows)
    if total < min_sample:
        return {
            "total_samples": total,
            "confident": False,
            "best_hours": [],
            "recommendation": (
                "Echantillon insuffisant, continuez a tracer les interactions entrantes."
            ),
        }

    top3 = [
        {
            "hour": int(r.hour),
            "count": int(r.count),
            "share": round(int(r.count) / total * 100, 1),
        }
        for r in rows[:3]
    ]
    best_hour = top3[0]["hour"] if top3 else None
    return {
        "total_samples": total,
        "confident": True,
        "best_hours": top3,
        "recommendation": (
            f"Preferez un contact autour de {best_hour}h — {top3[0]['share']}% "
            f"des reponses clients s'y concentrent."
            if best_hour is not None
            else "Aucune tendance claire."
        ),
    }
