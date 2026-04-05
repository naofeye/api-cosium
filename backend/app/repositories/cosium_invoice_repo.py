"""Repository for Cosium invoices — read-only queries."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cosium_data import CosiumInvoice


def get_list(
    db: Session,
    tenant_id: int,
    page: int = 1,
    page_size: int = 25,
    type_filter: str | None = None,
    settled: bool | None = None,
    search: str | None = None,
) -> tuple[list[CosiumInvoice], int]:
    """Return paginated Cosium invoices with optional filters."""
    q = select(CosiumInvoice).where(CosiumInvoice.tenant_id == tenant_id)
    q_count = select(func.count()).select_from(CosiumInvoice).where(CosiumInvoice.tenant_id == tenant_id)

    if type_filter:
        q = q.where(CosiumInvoice.type == type_filter)
        q_count = q_count.where(CosiumInvoice.type == type_filter)

    if settled is not None:
        q = q.where(CosiumInvoice.settled == settled)
        q_count = q_count.where(CosiumInvoice.settled == settled)

    if search:
        pattern = f"%{search}%"
        q = q.where(CosiumInvoice.invoice_number.ilike(pattern) | CosiumInvoice.customer_name.ilike(pattern))
        q_count = q_count.where(
            CosiumInvoice.invoice_number.ilike(pattern) | CosiumInvoice.customer_name.ilike(pattern)
        )

    total = db.scalar(q_count) or 0
    offset = (page - 1) * page_size
    rows = db.scalars(q.order_by(CosiumInvoice.invoice_date.desc().nullslast()).offset(offset).limit(page_size)).all()
    return list(rows), total
