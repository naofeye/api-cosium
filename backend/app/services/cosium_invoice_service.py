"""Service for Cosium invoice queries — pure business logic, no FastAPI dependency."""

from datetime import date

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.cosium_invoices import (
    CosiumInvoiceItem,
    CosiumInvoiceListResponse,
    CosiumInvoiceTotals,
)
from app.repositories import cosium_invoice_repo

logger = get_logger("cosium_invoice_service")


def list_invoices(
    db: Session,
    tenant_id: int,
    page: int = 1,
    page_size: int = 25,
    type_filter: str | None = None,
    settled: bool | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> CosiumInvoiceListResponse:
    """Return a paginated list of Cosium invoices."""
    rows, total = cosium_invoice_repo.get_list(
        db,
        tenant_id=tenant_id,
        page=page,
        page_size=page_size,
        type_filter=type_filter,
        settled=settled,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    items = [CosiumInvoiceItem.model_validate(row) for row in rows]
    logger.info(
        "cosium_invoices_listed",
        tenant_id=tenant_id,
        total=total,
        page=page,
        filters={"type": type_filter, "settled": settled, "search": search},
    )
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return CosiumInvoiceListResponse(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)


def get_totals(
    db: Session,
    tenant_id: int,
    type_filter: str | None = None,
    settled: bool | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> CosiumInvoiceTotals:
    """Return aggregate totals for current filters (across ALL pages)."""
    data = cosium_invoice_repo.get_totals(
        db,
        tenant_id=tenant_id,
        type_filter=type_filter,
        settled=settled,
        search=search,
        date_from=date_from,
        date_to=date_to,
    )
    return CosiumInvoiceTotals(
        total_ttc=data["total_ttc"],
        total_impaye=data["total_impaye"],
        count=data["count"],
    )
