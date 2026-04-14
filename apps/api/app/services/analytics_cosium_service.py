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
