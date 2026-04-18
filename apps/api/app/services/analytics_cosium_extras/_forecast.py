"""Prévisionnel tresorerie + tendances temporelles (période courante vs précédente)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cosium_data import CosiumInvoice
from app.services.analytics_cosium_service import _aging_bucket_sum


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
        "outstanding_total": round(
            aging_0_30 + aging_30_60 + aging_60_90 + aging_over_90, 2
        ),
        "expected_30d": round(expected_30d, 2),
        "irrecoverable_risk": round(irrecoverable_risk, 2),
        "buckets": {
            "0_30": round(aging_0_30, 2),
            "30_60": round(aging_30_60, 2),
            "60_90": round(aging_60_90, 2),
            "over_90": round(aging_over_90, 2),
        },
    }


def compute_trends(db: Session, tenant_id: int) -> dict:
    """Compare periode courante (30j) vs periode precedente (30j avant).

    Metriques : CA, nb factures, panier moyen.
    """
    now = datetime.now(UTC).replace(tzinfo=None)
    p1_end = now
    p1_start = now - timedelta(days=30)
    p2_end = p1_start
    p2_start = p2_end - timedelta(days=30)

    def _period(start: datetime, end: datetime) -> dict:
        row = db.execute(
            select(
                func.coalesce(func.sum(CosiumInvoice.total_ti), 0),
                func.count(),
            ).where(
                CosiumInvoice.tenant_id == tenant_id,
                CosiumInvoice.type == "INVOICE",
                CosiumInvoice.invoice_date >= start,
                CosiumInvoice.invoice_date < end,
            )
        ).one()
        ca = float(row[0] or 0)
        nb = int(row[1] or 0)
        panier = round(ca / nb, 2) if nb > 0 else 0.0
        return {"ca": round(ca, 2), "nb_factures": nb, "panier_moyen": panier}

    current = _period(p1_start, p1_end)
    previous = _period(p2_start, p2_end)

    def _delta_pct(a: float, b: float) -> float | None:
        if b == 0:
            return None
        return round((a - b) / b * 100, 1)

    return {
        "period_current": {
            "start": p1_start.date().isoformat(),
            "end": p1_end.date().isoformat(),
            **current,
        },
        "period_previous": {
            "start": p2_start.date().isoformat(),
            "end": p2_end.date().isoformat(),
            **previous,
        },
        "delta": {
            "ca_pct": _delta_pct(current["ca"], previous["ca"]),
            "nb_factures_pct": _delta_pct(current["nb_factures"], previous["nb_factures"]),
            "panier_moyen_pct": _delta_pct(current["panier_moyen"], previous["panier_moyen"]),
        },
    }
