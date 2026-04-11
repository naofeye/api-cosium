"""Tests for FEC (Fichier des Ecritures Comptables) export."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.models import Case, Customer, Facture, Payment, Tenant


def _seed_accounting_data(client: TestClient, headers: dict, db) -> None:
    """Seed invoices and payments for FEC tests."""
    tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
    tid = tenant.id

    # Create customer and case
    customer = Customer(
        tenant_id=tid, first_name="Jean", last_name="Dupont",
        email="jean@test.com",
    )
    db.add(customer)
    db.flush()

    case = Case(tenant_id=tid, customer_id=customer.id, status="en_cours")
    db.add(case)
    db.flush()

    # Create invoices
    f1 = Facture(
        tenant_id=tid, case_id=case.id, devis_id=0, numero="FAC-2025-001",
        date_emission=datetime(2025, 3, 15, tzinfo=UTC),
        montant_ht=100.00, tva=20.00, montant_ttc=120.00, status="payee",
    )
    f2 = Facture(
        tenant_id=tid, case_id=case.id, devis_id=0, numero="FAC-2025-002",
        date_emission=datetime(2025, 6, 20, tzinfo=UTC),
        montant_ht=250.50, tva=50.10, montant_ttc=300.60, status="emise",
    )
    db.add_all([f1, f2])
    db.flush()

    # Create a payment linked to f1
    p1 = Payment(
        tenant_id=tid, case_id=case.id, facture_id=f1.id,
        payer_type="client", mode_paiement="CB",
        reference_externe="PAY-REF-001",
        date_paiement=datetime(2025, 3, 20, tzinfo=UTC),
        amount_due=120.00, amount_paid=120.00, status="recu",
    )
    db.add(p1)
    db.commit()


def test_fec_export_basic(client: TestClient, auth_headers: dict, db) -> None:
    """Test that the FEC endpoint returns a valid tab-separated file."""
    _seed_accounting_data(client, auth_headers, db)

    resp = client.get(
        "/api/v1/exports/fec?date_from=2025-01-01&date_to=2025-12-31",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert "attachment" in resp.headers.get("content-disposition", "")
    assert "FEC_" in resp.headers["content-disposition"]

    # Check UTF-8 BOM
    raw = resp.content
    assert raw[:3] == b"\xef\xbb\xbf", "FEC must start with UTF-8 BOM"

    content = raw.decode("utf-8-sig")
    lines = content.strip().split("\n")

    # Header + at least data lines
    assert len(lines) >= 2, "FEC should have header + data lines"

    # Verify header columns
    header = lines[0].split("\t")
    assert header[0] == "JournalCode"
    assert header[-1] == "Idevise"
    assert len(header) == 18

    # Verify we have VE (sales) journal entries
    ve_lines = [l for l in lines[1:] if l.startswith("VE")]
    assert len(ve_lines) >= 4, "Should have debit+credit+TVA lines for 2 invoices"

    # Verify we have BQ (bank) journal entries
    bq_lines = [l for l in lines[1:] if l.startswith("BQ")]
    assert len(bq_lines) >= 2, "Should have debit+credit lines for 1 payment"


def test_fec_export_date_format(client: TestClient, auth_headers: dict, db) -> None:
    """Test that dates are in YYYYMMDD format."""
    _seed_accounting_data(client, auth_headers, db)

    resp = client.get(
        "/api/v1/exports/fec?date_from=2025-01-01&date_to=2025-12-31",
        headers=auth_headers,
    )
    content = resp.content.decode("utf-8-sig")
    lines = content.strip().split("\n")

    # Check a data line date format (EcritureDate is column index 3)
    first_data = lines[1].split("\t")
    ecriture_date = first_data[3]
    assert len(ecriture_date) == 8, "Date should be YYYYMMDD"
    assert ecriture_date.isdigit(), "Date should contain only digits"
    assert ecriture_date.startswith("2025"), "Date should start with 2025"


def test_fec_export_french_decimal(client: TestClient, auth_headers: dict, db) -> None:
    """Test that decimal separator is comma (French format)."""
    _seed_accounting_data(client, auth_headers, db)

    resp = client.get(
        "/api/v1/exports/fec?date_from=2025-01-01&date_to=2025-12-31",
        headers=auth_headers,
    )
    content = resp.content.decode("utf-8-sig")
    lines = content.strip().split("\n")

    # Check debit column (index 11) of first data line — should use comma
    first_data = lines[1].split("\t")
    debit_val = first_data[11]
    assert "," in debit_val, "Amounts should use comma as decimal separator"
    assert "." not in debit_val, "Amounts must NOT use dot as separator"


def test_fec_export_empty_range(client: TestClient, auth_headers: dict) -> None:
    """Test FEC with no data in range returns header only."""
    resp = client.get(
        "/api/v1/exports/fec?date_from=2099-01-01&date_to=2099-12-31",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    content = resp.content.decode("utf-8-sig")
    lines = content.strip().split("\n")
    assert len(lines) == 1, "Empty FEC should have header row only"


def test_fec_export_custom_siren(client: TestClient, auth_headers: dict) -> None:
    """Test that custom SIREN appears in filename."""
    resp = client.get(
        "/api/v1/exports/fec?date_from=2025-01-01&date_to=2025-12-31&siren=123456789",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    disposition = resp.headers["content-disposition"]
    assert "123456789" in disposition
    assert "20251231" in disposition


def test_fec_balanced_entries(client: TestClient, auth_headers: dict, db) -> None:
    """Test that each ecriture is balanced (total debit == total credit)."""
    _seed_accounting_data(client, auth_headers, db)

    resp = client.get(
        "/api/v1/exports/fec?date_from=2025-01-01&date_to=2025-12-31",
        headers=auth_headers,
    )
    content = resp.content.decode("utf-8-sig")
    lines = content.strip().split("\n")

    # Group by EcritureNum (index 2) and check balance
    entries: dict[str, list[tuple[float, float]]] = {}
    for line in lines[1:]:
        cols = line.split("\t")
        ecriture_num = cols[2]
        debit = float(cols[11].replace(",", "."))
        credit = float(cols[12].replace(",", "."))
        entries.setdefault(ecriture_num, []).append((debit, credit))

    for ecriture_num, rows in entries.items():
        total_debit = sum(d for d, _ in rows)
        total_credit = sum(c for _, c in rows)
        assert abs(total_debit - total_credit) < 0.01, (
            f"Ecriture {ecriture_num} is not balanced: "
            f"debit={total_debit:.2f} credit={total_credit:.2f}"
        )
