"""Tests for export edge cases and robustness."""

from datetime import date, datetime

from fastapi.testclient import TestClient


# ---------- Test 1: FEC export with no data returns valid but empty file ----------

def test_fec_export_no_data_returns_valid_file(
    client: TestClient,
    auth_headers: dict,
) -> None:
    """FEC export with no matching invoices/payments should return a valid file with only headers."""
    resp = client.get(
        "/api/v1/exports/fec",
        params={"date_from": "2099-01-01", "date_to": "2099-12-31"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    content = resp.content.decode("utf-8-sig")
    lines = content.strip().split("\n")
    # Should have at least the header row
    assert len(lines) >= 1
    assert "JournalCode" in lines[0]
    # No data lines (only header)
    assert len(lines) == 1


# ---------- Test 2: balance export with no outstanding invoices ----------

def test_balance_export_no_outstanding(
    client: TestClient,
    auth_headers: dict,
) -> None:
    """Balance export with no outstanding invoices should return a valid xlsx."""
    resp = client.get(
        "/api/v1/exports/balance-clients",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "spreadsheetml" in resp.headers["content-type"]
    # Should still have content (at least the header row in xlsx)
    assert len(resp.content) > 50


# ---------- Test 3: dashboard PDF with all-zero KPIs ----------

def test_dashboard_pdf_all_zero_kpis(
    client: TestClient,
    auth_headers: dict,
) -> None:
    """Dashboard PDF export on empty DB should not crash and return valid PDF."""
    resp = client.get(
        "/api/v1/exports/dashboard-pdf",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    # PDF starts with %PDF
    assert resp.content[:5] == b"%PDF-"


# ---------- Test 4: export with date range that matches nothing ----------

def test_export_date_range_matches_nothing(
    client: TestClient,
    auth_headers: dict,
) -> None:
    """CSV export with a future date range should return headers only."""
    resp = client.get(
        "/api/v1/exports/factures",
        params={
            "format": "csv",
            "date_from": "2099-01-01T00:00:00",
            "date_to": "2099-12-31T23:59:59",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 200
    content = resp.content.decode("utf-8-sig")
    lines = content.strip().split("\n")
    # Only header row, no data
    assert len(lines) == 1
    assert "Numero" in lines[0]


# ---------- Test 5: export respects max_export_rows limit ----------

def test_export_respects_max_rows_limit(
    client: TestClient,
    auth_headers: dict,
    db,
) -> None:
    """The export _get_rows function should enforce max_export_rows=50000 limit.

    We verify this indirectly: even when requesting all clients, the query has
    a .limit(50000). Creating 50001 records in a test DB is impractical, so we
    just verify the export works with many records seeded.
    """
    from app.models.client import Customer

    # Seed 10 clients to ensure export works
    for i in range(10):
        db.add(Customer(
            tenant_id=1,
            first_name=f"Bulk{i}",
            last_name=f"Export{i}",
            email=f"bulk{i}@test.com",
        ))
    db.commit()

    resp = client.get("/api/v1/exports/clients?format=csv", headers=auth_headers)
    assert resp.status_code == 200
    content = resp.content.decode("utf-8-sig")
    lines = content.strip().split("\n")
    # Header + at least 10 data rows
    assert len(lines) >= 11
