"""Re-link orphan CosiumPrescription rows to customers using multiple strategies.

Strategies (in order):
1. Invoice number from spectacles_json -> CosiumInvoice -> customer_id
2. Date proximity: prescription date within 7 days of a CosiumInvoice -> customer_id
3. OCR document cross-reference: search prescription data in document extractions

Usage:
    docker compose exec api python -m scripts.relink_prescriptions
"""

import json
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import func as sa_func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Customer, Tenant
from app.models.cosium_data import CosiumDocument, CosiumInvoice, CosiumPrescription
from app.models.document_extraction import DocumentExtraction

BATCH_SIZE = 500


def _build_cosium_id_to_customer_map(db: Session, tenant_id: int) -> dict[str, int]:
    """Build a mapping from cosium_id -> customer.id for a tenant."""
    customers = db.scalars(
        select(Customer).where(
            Customer.tenant_id == tenant_id,
            Customer.cosium_id.isnot(None),
        )
    ).all()
    return {str(c.cosium_id): c.id for c in customers}


def _extract_invoice_numbers_from_spectacles(spectacles_json: str | None) -> list[str]:
    """Extract invoice numbers from spectacles_json field."""
    if not spectacles_json:
        return []
    try:
        data = json.loads(spectacles_json)
        numbers: list[str] = []
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict):
                for key in ("invoiceNumber", "invoice_number", "factureNumero", "numero_facture"):
                    val = item.get(key)
                    if val:
                        numbers.append(str(val))
        return numbers
    except (json.JSONDecodeError, TypeError):
        return []


def _strategy_invoice_number(
    db: Session,
    tenant_id: int,
    prescription: CosiumPrescription,
    cosium_id_map: dict[str, int],
) -> int | None:
    """Strategy 1: Link via invoice number found in spectacles_json."""
    invoice_numbers = _extract_invoice_numbers_from_spectacles(prescription.spectacles_json)
    for inv_num in invoice_numbers:
        invoice = db.scalars(
            select(CosiumInvoice).where(
                CosiumInvoice.tenant_id == tenant_id,
                CosiumInvoice.invoice_number == inv_num,
            ).limit(1)
        ).first()
        if invoice and invoice.customer_id:
            return invoice.customer_id
        if invoice and invoice.customer_cosium_id:
            cid = cosium_id_map.get(str(invoice.customer_cosium_id))
            if cid:
                return cid
    return None


def _strategy_date_proximity(
    db: Session,
    tenant_id: int,
    prescription: CosiumPrescription,
    cosium_id_map: dict[str, int],
) -> int | None:
    """Strategy 2: Find invoice within 7 days of prescription date."""
    if not prescription.file_date:
        return None

    rx_date = prescription.file_date
    date_start = rx_date - timedelta(days=7)
    date_end = rx_date + timedelta(days=7)

    # Find invoices in the date range that have a customer link
    invoice = db.scalars(
        select(CosiumInvoice).where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.invoice_date.isnot(None),
            CosiumInvoice.invoice_date >= date_start,
            CosiumInvoice.invoice_date <= date_end,
            CosiumInvoice.customer_id.isnot(None),
        ).order_by(
            sa_func.abs(
                sa_func.extract("epoch", CosiumInvoice.invoice_date)
                - sa_func.extract("epoch", sa_func.cast(rx_date, CosiumInvoice.invoice_date.type))
            )
        ).limit(1)
    ).first()

    if invoice and invoice.customer_id:
        return invoice.customer_id
    return None


def _strategy_ocr_cross_reference(
    db: Session,
    tenant_id: int,
    prescription: CosiumPrescription,
    cosium_id_map: dict[str, int],
) -> int | None:
    """Strategy 3: Cross-reference with OCR document extractions.

    Search for prescriber name in document extraction text to find the customer.
    """
    if not prescription.prescriber_name or len(prescription.prescriber_name.strip()) < 4:
        return None

    prescriber_upper = prescription.prescriber_name.strip().upper()

    # Search for this prescriber in ordonnance extractions that have a customer link
    match = db.scalars(
        select(CosiumDocument.customer_cosium_id).join(
            DocumentExtraction,
            (CosiumDocument.cosium_document_id == DocumentExtraction.cosium_document_id)
            & (CosiumDocument.tenant_id == DocumentExtraction.tenant_id),
        ).where(
            CosiumDocument.tenant_id == tenant_id,
            CosiumDocument.customer_cosium_id.isnot(None),
            DocumentExtraction.document_type == "ordonnance",
            sa_func.upper(DocumentExtraction.raw_text).contains(prescriber_upper),
        ).limit(1)
    ).first()

    if match:
        return cosium_id_map.get(str(match))
    return None


def relink_prescriptions_via_documents(db: Session, tenant_id: int) -> dict:
    """Link prescriptions to customers using multiple cross-reference strategies."""
    cosium_id_map = _build_cosium_id_to_customer_map(db, tenant_id)

    orphans = db.scalars(
        select(CosiumPrescription).where(
            CosiumPrescription.tenant_id == tenant_id,
            CosiumPrescription.customer_id.is_(None),
        )
    ).all()

    linked_by_invoice = 0
    linked_by_date = 0
    linked_by_ocr = 0
    still_orphan = 0
    processed = 0

    for presc in orphans:
        customer_id = None

        # Strategy 1: invoice number from spectacles_json
        customer_id = _strategy_invoice_number(db, tenant_id, presc, cosium_id_map)
        if customer_id:
            presc.customer_id = customer_id
            linked_by_invoice += 1
        else:
            # Strategy 2: date proximity
            customer_id = _strategy_date_proximity(db, tenant_id, presc, cosium_id_map)
            if customer_id:
                presc.customer_id = customer_id
                linked_by_date += 1
            else:
                # Strategy 3: OCR cross-reference
                customer_id = _strategy_ocr_cross_reference(db, tenant_id, presc, cosium_id_map)
                if customer_id:
                    presc.customer_id = customer_id
                    linked_by_ocr += 1
                else:
                    still_orphan += 1

        processed += 1
        if processed % BATCH_SIZE == 0:
            db.flush()

    db.commit()
    return {
        "total_orphans": len(orphans),
        "linked_by_invoice_number": linked_by_invoice,
        "linked_by_date_proximity": linked_by_date,
        "linked_by_ocr": linked_by_ocr,
        "still_orphan": still_orphan,
    }


def main() -> None:
    db = SessionLocal()
    try:
        tenants = db.scalars(select(Tenant)).all()
        for tenant in tenants:
            print(f"\n=== Tenant: {tenant.name} (id={tenant.id}) ===")
            stats = relink_prescriptions_via_documents(db, tenant.id)
            print(f"  Prescription Relink: {stats}")
            total_linked = (
                stats["linked_by_invoice_number"]
                + stats["linked_by_date_proximity"]
                + stats["linked_by_ocr"]
            )
            pct = round(total_linked / stats["total_orphans"] * 100, 1) if stats["total_orphans"] > 0 else 0
            print(f"  Total linked: {total_linked}/{stats['total_orphans']} ({pct}%)")
        print("\nDone.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
