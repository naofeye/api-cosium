"""Repository for Cosium invoices — read-only queries."""

from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cosium_data import CosiumInvoice


def _apply_filters(
    q,
    tenant_id: int,
    type_filter: str | None = None,
    settled: bool | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
):
    """Apply common filters to a query (shared between data query and count)."""
    q = q.where(CosiumInvoice.tenant_id == tenant_id)

    if type_filter:
        q = q.where(CosiumInvoice.type == type_filter)

    if settled is not None:
        q = q.where(CosiumInvoice.settled == settled)

    if search:
        pattern = f"%{search}%"
        q = q.where(CosiumInvoice.invoice_number.ilike(pattern) | CosiumInvoice.customer_name.ilike(pattern))

    if date_from:
        q = q.where(CosiumInvoice.invoice_date >= datetime.combine(date_from, datetime.min.time()))

    if date_to:
        q = q.where(CosiumInvoice.invoice_date <= datetime.combine(date_to, datetime.max.time()))

    return q


def get_list(
    db: Session,
    tenant_id: int,
    page: int = 1,
    page_size: int = 25,
    type_filter: str | None = None,
    settled: bool | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> tuple[list[CosiumInvoice], int]:
    """Return paginated Cosium invoices with optional filters."""
    q = _apply_filters(
        select(CosiumInvoice), tenant_id, type_filter, settled, search, date_from, date_to,
    )
    q_count = _apply_filters(
        select(func.count()).select_from(CosiumInvoice), tenant_id, type_filter, settled, search, date_from, date_to,
    )

    total = db.scalar(q_count) or 0
    offset = (page - 1) * page_size
    rows = db.scalars(q.order_by(CosiumInvoice.invoice_date.desc().nullslast()).offset(offset).limit(page_size)).all()
    return list(rows), total


def get_totals(
    db: Session,
    tenant_id: int,
    type_filter: str | None = None,
    settled: bool | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict[str, float | int]:
    """Return aggregate totals for filtered invoices (across ALL pages)."""
    base = select(
        func.coalesce(func.sum(CosiumInvoice.total_ti), 0).label("total_ttc"),
        func.coalesce(func.sum(CosiumInvoice.outstanding_balance), 0).label("total_impaye"),
        func.count().label("count"),
    ).select_from(CosiumInvoice)

    q = _apply_filters(base, tenant_id, type_filter, settled, search, date_from, date_to)
    row = db.execute(q).first()
    if not row:
        return {"total_ttc": 0.0, "total_impaye": 0.0, "count": 0}
    return {
        "total_ttc": float(row.total_ttc),
        "total_impaye": float(row.total_impaye),
        "count": int(row.count),
    }


def get_totals_by_type(
    db: Session,
    tenant_id: int,
) -> list[dict[str, str | float | int]]:
    """Return aggregate totals grouped by invoice type."""
    q = (
        select(
            CosiumInvoice.type,
            func.coalesce(func.sum(CosiumInvoice.total_ti), 0).label("total_ttc"),
            func.coalesce(func.sum(CosiumInvoice.outstanding_balance), 0).label("total_impaye"),
            func.count().label("count"),
        )
        .select_from(CosiumInvoice)
        .where(CosiumInvoice.tenant_id == tenant_id)
        .group_by(CosiumInvoice.type)
    )
    rows = db.execute(q).all()
    return [
        {
            "type": row.type,
            "total_ttc": float(row.total_ttc),
            "total_impaye": float(row.total_impaye),
            "count": int(row.count),
        }
        for row in rows
    ]
