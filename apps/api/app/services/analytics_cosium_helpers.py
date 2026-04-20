"""Helper/computation functions for Cosium analytics.

Extracted from analytics_cosium_service.py to keep files under 300 lines.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cosium_data import CosiumInvoice


def sum_invoices_between(db: Session, tenant_id: int, start: datetime, end: datetime) -> float:
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


def count_invoices_between(db: Session, tenant_id: int, start: datetime, end: datetime) -> int:
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


def aging_bucket_sum(db: Session, tenant_id: int, days_min: int, days_max: int | None) -> float:
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
