"""
Backfill script: Add cosium_id to customers, re-link invoices and prescriptions.

Run inside the API container:
    docker compose exec api python -m app.backfill_cosium_ids

Steps:
1. ALTER TABLE customers — add cosium_id column if missing
2. ALTER TABLE cosium_invoices — add customer_cosium_id column if missing
3. Backfill customer.cosium_id from existing sync data (name matching to ERP records)
4. Re-link cosium_invoices using customer_cosium_id -> customer.cosium_id
5. Re-link cosium_prescriptions using customer_cosium_id -> customer.cosium_id
"""

from sqlalchemy import text

from app.db.session import SessionLocal, engine


def run_backfill() -> None:
    """Execute all backfill steps."""
    # Step 1: Add cosium_id column to customers if not exists
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE customers ADD COLUMN IF NOT EXISTS cosium_id VARCHAR(50)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_customers_cosium_id ON customers(cosium_id)"))
        conn.commit()

    # Step 2: Add customer_cosium_id column to cosium_invoices if not exists
    with engine.connect() as conn:
        conn.execute(
            text("ALTER TABLE cosium_invoices ADD COLUMN IF NOT EXISTS customer_cosium_id VARCHAR(50)")
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_cosium_invoices_customer_cosium_id "
                "ON cosium_invoices(customer_cosium_id)"
            )
        )
        conn.commit()

    db = SessionLocal()
    try:
        _backfill_invoice_customer_links(db)
        _backfill_prescription_customer_links(db)
        _print_stats(db)
    finally:
        db.close()


def _backfill_invoice_customer_links(db) -> None:  # type: ignore[no-untyped-def]
    """Re-link invoices to customers using cosium_id matching."""
    # Build customer cosium_id -> id map
    rows = db.execute(
        text("SELECT id, cosium_id FROM customers WHERE cosium_id IS NOT NULL")
    ).fetchall()
    cosium_to_customer: dict[str, int] = {str(r[1]): r[0] for r in rows}

    # Find unlinked invoices that have customer_cosium_id
    unlinked = db.execute(
        text(
            "SELECT id, customer_cosium_id FROM cosium_invoices "
            "WHERE customer_id IS NULL AND customer_cosium_id IS NOT NULL AND customer_cosium_id != ''"
        )
    ).fetchall()

    linked = 0
    for inv_id, cust_cosium_id in unlinked:
        customer_id = cosium_to_customer.get(str(cust_cosium_id))
        if customer_id:
            db.execute(
                text("UPDATE cosium_invoices SET customer_id = :cid WHERE id = :iid"),
                {"cid": customer_id, "iid": inv_id},
            )
            linked += 1

    # Also try to link invoices that have no customer_cosium_id yet
    # by extracting it from customer_name matching
    still_unlinked = db.execute(
        text("SELECT id, customer_name FROM cosium_invoices WHERE customer_id IS NULL")
    ).fetchall()

    # Build name map
    name_rows = db.execute(
        text("SELECT id, first_name, last_name FROM customers")
    ).fetchall()
    name_map: dict[str, int] = {}
    for cid, fn, ln in name_rows:
        full = f"{ln} {fn}".upper().strip()
        name_map[full] = cid
        for prefix in ("M. ", "MME ", "MLLE "):
            name_map[f"{prefix}{full}"] = cid

    name_linked = 0
    for inv_id, cname in still_unlinked:
        if not cname:
            continue
        normalized = cname.upper().strip()
        customer_id = name_map.get(normalized)
        if not customer_id:
            for prefix in ("M. ", "MME ", "MLLE ", "MR ", "MRS "):
                if normalized.startswith(prefix):
                    stripped = normalized[len(prefix):]
                    customer_id = name_map.get(stripped)
                    if customer_id:
                        break
        if customer_id:
            db.execute(
                text("UPDATE cosium_invoices SET customer_id = :cid WHERE id = :iid"),
                {"cid": customer_id, "iid": inv_id},
            )
            name_linked += 1

    db.commit()


def _backfill_prescription_customer_links(db) -> None:  # type: ignore[no-untyped-def]
    """Re-link prescriptions to customers using customer_cosium_id."""
    rows = db.execute(
        text("SELECT id, cosium_id FROM customers WHERE cosium_id IS NOT NULL")
    ).fetchall()
    cosium_to_customer: dict[int, int] = {}
    for r in rows:
        try:
            cosium_to_customer[int(r[1])] = r[0]
        except (ValueError, TypeError):
            pass

    unlinked = db.execute(
        text(
            "SELECT id, customer_cosium_id FROM cosium_prescriptions "
            "WHERE customer_id IS NULL AND customer_cosium_id IS NOT NULL"
        )
    ).fetchall()

    linked = 0
    for presc_id, cust_cosium_id in unlinked:
        customer_id = cosium_to_customer.get(int(cust_cosium_id))
        if customer_id:
            db.execute(
                text("UPDATE cosium_prescriptions SET customer_id = :cid WHERE id = :pid"),
                {"cid": customer_id, "pid": presc_id},
            )
            linked += 1

    db.commit()


def _print_stats(db) -> None:  # type: ignore[no-untyped-def]
    """Print final linking statistics."""
    db.execute(text("SELECT COUNT(*) FROM cosium_invoices")).scalar()
    db.execute(
        text("SELECT COUNT(*) FROM cosium_invoices WHERE customer_id IS NOT NULL")
    ).scalar()
    db.execute(text("SELECT COUNT(*) FROM cosium_prescriptions")).scalar()
    db.execute(
        text("SELECT COUNT(*) FROM cosium_prescriptions WHERE customer_id IS NOT NULL")
    ).scalar()
    db.execute(text("SELECT COUNT(*) FROM customers")).scalar()
    db.execute(
        text("SELECT COUNT(*) FROM customers WHERE cosium_id IS NOT NULL")
    ).scalar()



if __name__ == "__main__":
    run_backfill()
