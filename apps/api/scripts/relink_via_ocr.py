"""Re-link orphan CosiumInvoice rows to customers using OCR document text cross-reference.

Strategy: For each unlinked invoice, search the customerName in DocumentExtraction.raw_text.
If found, the document belongs to a customer (via CosiumDocument.customer_cosium_id),
so the invoice can be linked to that customer.

Usage:
    docker compose exec api python -m scripts.relink_via_ocr
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func as sa_func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Customer, Tenant
from app.models.cosium_data import CosiumDocument, CosiumInvoice
from app.models.document_extraction import DocumentExtraction
from app.services.erp_sync_service import _normalize_name

BATCH_SIZE = 500


def _build_cosium_id_to_customer_map(
    db: Session, tenant_id: int
) -> dict[str, int]:
    """Build a mapping from cosium_id -> customer.id for a tenant."""
    customers = db.scalars(
        select(Customer).where(
            Customer.tenant_id == tenant_id,
            Customer.cosium_id.isnot(None),
        )
    ).all()
    return {str(c.cosium_id): c.id for c in customers}


def _extract_search_name(customer_name: str) -> str:
    """Extract the meaningful part of a customerName, stripping titles."""
    normalized = _normalize_name(customer_name)
    for prefix in (
        "M. ", "MME. ", "MLLE. ", "MME ", "MLLE ",
        "MR. ", "MR ", "MRS. ", "MRS ", "DR. ", "DR ",
    ):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):]
            break
    return normalized.strip()


def relink_invoices_via_documents(db: Session, tenant_id: int) -> dict:
    """Try to link orphan invoices by cross-referencing with document text."""
    cosium_map = _build_cosium_id_to_customer_map(db, tenant_id)

    orphans = db.scalars(
        select(CosiumInvoice).where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.customer_id.is_(None),
            CosiumInvoice.customer_name.isnot(None),
        )
    ).all()

    linked = 0
    still_orphan = 0
    processed = 0

    for inv in orphans:
        if not inv.customer_name:
            still_orphan += 1
            continue

        search_name = _extract_search_name(inv.customer_name)
        if len(search_name) < 4:
            still_orphan += 1
            continue

        # Search for this name in OCR raw_text across CosiumDocuments for this tenant
        match = db.scalars(
            select(CosiumDocument.customer_cosium_id).join(
                DocumentExtraction,
                (CosiumDocument.cosium_document_id == DocumentExtraction.cosium_document_id)
                & (CosiumDocument.tenant_id == DocumentExtraction.tenant_id),
            ).where(
                CosiumDocument.tenant_id == tenant_id,
                CosiumDocument.customer_cosium_id.isnot(None),
                sa_func.upper(DocumentExtraction.raw_text).contains(search_name),
            ).limit(1)
        ).first()

        if match:
            customer_id = cosium_map.get(str(match))
            if customer_id:
                inv.customer_id = customer_id
                linked += 1
            else:
                still_orphan += 1
        else:
            still_orphan += 1

        processed += 1
        if processed % BATCH_SIZE == 0:
            db.flush()

    db.commit()
    return {
        "total_orphans": len(orphans),
        "linked_via_ocr": linked,
        "still_orphan": still_orphan,
    }


def main() -> None:
    db = SessionLocal()
    try:
        tenants = db.scalars(select(Tenant)).all()
        for tenant in tenants:
            print(f"\n=== Tenant: {tenant.name} (id={tenant.id}) ===")
            stats = relink_invoices_via_documents(db, tenant.id)
            print(f"  OCR Relink: {stats}")
        print("\nDone.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
