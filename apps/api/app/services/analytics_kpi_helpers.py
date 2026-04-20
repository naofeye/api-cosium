"""Helper KPI functions for analytics: commercial and marketing KPIs.

Extracted from analytics_kpi_service.py to keep files under 300 lines.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.constants import DEVIS_BROUILLON, DEVIS_ENVOYE, DEVIS_SIGNE
from app.domain.schemas.analytics import CommercialKPIs, MarketingKPIs
from app.models import Campaign, Devis, Facture, MessageLog


def get_commercial_kpis(db: Session, tenant_id: int) -> CommercialKPIs:
    devis_total = db.scalar(select(func.count()).select_from(Devis).where(Devis.tenant_id == tenant_id)) or 0
    devis_brouillon = (
        db.scalar(
            select(func.count())
            .select_from(Devis)
            .where(Devis.tenant_id == tenant_id, Devis.status.in_([DEVIS_BROUILLON, DEVIS_ENVOYE]))
        )
        or 0
    )
    devis_signes = (
        db.scalar(
            select(func.count())
            .select_from(Devis)
            .where(Devis.tenant_id == tenant_id, Devis.status.in_([DEVIS_SIGNE, "facture"]))
        )
        or 0
    )
    taux = round(devis_signes / devis_total * 100, 1) if devis_total > 0 else 0

    avg = db.scalar(
        select(func.avg(Devis.montant_ttc)).where(Devis.tenant_id == tenant_id, Devis.status.in_([DEVIS_SIGNE, "facture"]))
    )
    panier_moyen = round(Decimal(str(avg)), 2) if avg else 0

    ca_mois = _build_ca_par_mois(db, tenant_id)

    return CommercialKPIs(
        devis_en_cours=devis_brouillon,
        devis_signes=devis_signes,
        taux_conversion=taux,
        panier_moyen=panier_moyen,
        ca_par_mois=ca_mois,
    )


def _build_ca_par_mois(db: Session, tenant_id: int) -> list[dict]:
    """Return CA per month for the last 6 months (current month included)."""
    ca_mois = []
    now = datetime.now(UTC).replace(tzinfo=None)
    for i in range(5, -1, -1):
        target_month = now.month - i
        target_year = now.year
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        month_start = datetime(target_year, target_month, 1)
        next_month = (month_start + timedelta(days=32)).replace(day=1) if i > 0 else now
        ca = (
            db.scalar(
                select(func.coalesce(func.sum(Facture.montant_ttc), 0))
                .where(Facture.tenant_id == tenant_id)
                .where(Facture.created_at >= month_start, Facture.created_at < next_month)
            )
            or 0
        )
        ca_mois.append({"mois": month_start.strftime("%Y-%m"), "ca": round(Decimal(str(ca)), 2)})
    return ca_mois


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
