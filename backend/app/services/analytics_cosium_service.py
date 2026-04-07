"""Cosium-specific KPI calculations for the analytics dashboard.

Contains KPI functions that query Cosium-synced data (invoices, customers,
calendar events, prescriptions, payments).
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.analytics import (
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
