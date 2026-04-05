"""Service for Cosium invoice queries — pure business logic, no FastAPI dependency."""

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.cosium_invoices import CosiumInvoiceItem, CosiumInvoiceListResponse
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
    )
    items = [CosiumInvoiceItem.model_validate(row) for row in rows]
    logger.info(
        "cosium_invoices_listed",
        tenant_id=tenant_id,
        total=total,
        page=page,
        filters={"type": type_filter, "settled": settled, "search": search},
    )
    return CosiumInvoiceListResponse(items=items, total=total, page=page, page_size=page_size)
