"""Re-link orphan CosiumInvoice and CosiumPayment rows to customers.

Strategies (in order):
1. cosium_id direct match (customer_cosium_id -> Customer.cosium_id)
2. Normalized name match (customer_name -> Customer last+first)
3. Fuzzy match (rapidfuzz, score >= 85)

Usage:
    docker compose exec api python -m scripts.relink_orphan_data
"""

import sys
from pathlib import Path

# Add backend to path so 'app' is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models import Customer, Tenant
from app.models.cosium_data import CosiumInvoice, CosiumPayment, CosiumPrescription
from app.services.erp_sync_service import _match_customer_by_name, _normalize_name


def _build_customer_maps(
    db: Session, tenant_id: int
) -> tuple[dict[str, int], dict[str, int]]:
    """Build cosium_id map and normalized name map for a tenant."""
    all_customers = db.scalars(
        select(Customer).where(Customer.tenant_id == tenant_id)
    ).all()

    cosium_id_map: dict[str, int] = {}
    name_map: dict[str, int] = {}

    for c in all_customers:
        if c.cosium_id:
            cosium_id_map[str(c.cosium_id)] = c.id
        normalized_full = _normalize_name(f"{c.last_name} {c.first_name}")
        name_map[normalized_full] = c.id
        normalized_reverse = _normalize_name(f"{c.first_name} {c.last_name}")
        name_map[normalized_reverse] = c.id

    return cosium_id_map, name_map


def relink_invoices(db: Session, tenant_id: int) -> dict:
    """Re-link orphan invoices for a tenant."""
    cosium_id_map, name_map = _build_customer_maps(db, tenant_id)

    orphans = db.scalars(
        select(CosiumInvoice).where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.customer_id.is_(None),
        )
    ).all()

    linked_by_cosium_id = 0
    linked_by_name = 0
    still_orphan = 0

    for inv in orphans:
        customer_id = None

        # Strategy 1: cosium_id match
        if inv.customer_cosium_id:
            customer_id = cosium_id_map.get(str(inv.customer_cosium_id))
            if customer_id:
                linked_by_cosium_id += 1

        # Strategy 2+3: name match (includes fuzzy)
        if not customer_id and inv.customer_name:
            customer_id = _match_customer_by_name(inv.customer_name, name_map)
            if customer_id:
                linked_by_name += 1

        if customer_id:
            inv.customer_id = customer_id
        else:
            still_orphan += 1

    db.commit()
    return {
        "total_orphans": len(orphans),
        "linked_by_cosium_id": linked_by_cosium_id,
        "linked_by_name": linked_by_name,
        "still_orphan": still_orphan,
    }


def relink_payments(db: Session, tenant_id: int) -> dict:
    """Re-link orphan payments for a tenant."""
    cosium_id_map, name_map = _build_customer_maps(db, tenant_id)

    orphans = db.scalars(
        select(CosiumPayment).where(
            CosiumPayment.tenant_id == tenant_id,
            CosiumPayment.customer_id.is_(None),
        )
    ).all()

    linked_by_cosium_id = 0
    linked_by_name = 0
    still_orphan = 0

    for pmt in orphans:
        customer_id = None

        # Strategy 1: cosium_id match
        if pmt.customer_cosium_id:
            customer_id = cosium_id_map.get(str(pmt.customer_cosium_id))
            if customer_id:
                linked_by_cosium_id += 1

        # Strategy 2+3: name match (includes fuzzy via issuer_name)
        if not customer_id and pmt.issuer_name:
            customer_id = _match_customer_by_name(pmt.issuer_name, name_map)
            if customer_id:
                linked_by_name += 1

        if customer_id:
            pmt.customer_id = customer_id
        else:
            still_orphan += 1

    db.commit()
    return {
        "total_orphans": len(orphans),
        "linked_by_cosium_id": linked_by_cosium_id,
        "linked_by_name": linked_by_name,
        "still_orphan": still_orphan,
    }


def relink_prescriptions(db: Session, tenant_id: int) -> dict:
    """Re-link orphan prescriptions for a tenant."""
    cosium_id_map, _ = _build_customer_maps(db, tenant_id)

    orphans = db.scalars(
        select(CosiumPrescription).where(
            CosiumPrescription.tenant_id == tenant_id,
            CosiumPrescription.customer_id.is_(None),
        )
    ).all()

    linked = 0
    still_orphan = 0

    for presc in orphans:
        customer_id = None
        if presc.customer_cosium_id:
            customer_id = cosium_id_map.get(str(presc.customer_cosium_id))

        if customer_id:
            presc.customer_id = customer_id
            linked += 1
        else:
            still_orphan += 1

    db.commit()
    return {"total_orphans": len(orphans), "linked": linked, "still_orphan": still_orphan}


def main() -> None:
    db = SessionLocal()
    try:
        tenants = db.scalars(select(Tenant)).all()
        for tenant in tenants:
            print(f"\n=== Tenant: {tenant.name} (id={tenant.id}) ===")

            inv_stats = relink_invoices(db, tenant.id)
            print(f"  Invoices: {inv_stats}")

            pmt_stats = relink_payments(db, tenant.id)
            print(f"  Payments: {pmt_stats}")

            presc_stats = relink_prescriptions(db, tenant.id)
            print(f"  Prescriptions: {presc_stats}")

        print("\nDone.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
