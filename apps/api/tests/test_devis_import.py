"""Tests for devis_import_service — Cosium QUOTE to OptiFlow Devis conversion."""

import pytest
from datetime import UTC, datetime

from app.models.case import Case
from app.models.client import Customer
from app.models.cosium_data import CosiumInvoice
from app.models.devis import Devis, DevisLigne
from app.services.devis_import_service import import_cosium_quotes_as_devis


def _create_customer(db, tenant_id: int, cosium_id: str = "C100") -> Customer:
    customer = Customer(
        tenant_id=tenant_id,
        cosium_id=cosium_id,
        first_name="Jean",
        last_name="Dupont",
    )
    db.add(customer)
    db.flush()
    return customer


def _create_quote(
    db,
    tenant_id: int,
    customer_id: int | None,
    invoice_number: str = "D100001",
    total_ti: float = 500.0,
    secu: float = 10.0,
    mutuelle: float = 300.0,
) -> CosiumInvoice:
    quote = CosiumInvoice(
        tenant_id=tenant_id,
        cosium_id=hash(invoice_number) % 100000,
        invoice_number=invoice_number,
        invoice_date=datetime.now(UTC),
        customer_name="DUPONT Jean",
        customer_id=customer_id,
        type="QUOTE",
        total_ti=total_ti,
        share_social_security=secu,
        share_private_insurance=mutuelle,
    )
    db.add(quote)
    db.flush()
    return quote


class TestDevisImportCreatesDevis:
    """Test 1: Import creates devis from Cosium quote."""

    def test_basic_import(self, db, default_tenant):
        tid = default_tenant.id
        customer = _create_customer(db, tid)
        _create_quote(db, tid, customer.id, "D999001", 600.0, 5.0, 400.0)
        db.commit()

        result = import_cosium_quotes_as_devis(db, tid, user_id=1)

        assert result["imported"] == 1
        assert result["errors"] == 0

        devis = db.query(Devis).filter(Devis.numero == "D999001").first()
        assert devis is not None
        assert devis.status == "signe"
        assert float(devis.montant_ttc) == 600.0
        assert float(devis.part_secu) == 5.0
        assert float(devis.part_mutuelle) == 400.0

        # Verify line item was created
        ligne = db.query(DevisLigne).filter(DevisLigne.devis_id == devis.id).first()
        assert ligne is not None
        assert ligne.quantite == 1
        assert "optique" in ligne.designation.lower()


class TestDevisImportSkipsDuplicates:
    """Test 2: Import skips already-imported quotes."""

    def test_idempotent(self, db, default_tenant):
        tid = default_tenant.id
        customer = _create_customer(db, tid)
        _create_quote(db, tid, customer.id, "D999002", 800.0, 10.0, 500.0)
        db.commit()

        result1 = import_cosium_quotes_as_devis(db, tid, user_id=1)
        assert result1["imported"] == 1

        result2 = import_cosium_quotes_as_devis(db, tid, user_id=1)
        assert result2["imported"] == 0
        assert result2["skipped"] == 1

        # Still only one devis
        count = db.query(Devis).filter(Devis.numero == "D999002").count()
        assert count == 1


class TestDevisImportCreatesCaseIfNeeded:
    """Test 3: Import creates case if customer has none."""

    def test_creates_case(self, db, default_tenant):
        tid = default_tenant.id
        customer = _create_customer(db, tid)
        # No existing case for this customer
        _create_quote(db, tid, customer.id, "D999003")
        db.commit()

        result = import_cosium_quotes_as_devis(db, tid, user_id=1)

        assert result["imported"] == 1
        case = db.query(Case).filter(
            Case.customer_id == customer.id,
            Case.tenant_id == tid,
        ).first()
        assert case is not None
        assert case.source == "cosium"
        assert case.status == "complet"

    def test_uses_existing_case(self, db, default_tenant):
        tid = default_tenant.id
        customer = _create_customer(db, tid)
        existing_case = Case(
            tenant_id=tid,
            customer_id=customer.id,
            status="en_cours",
            source="manual",
        )
        db.add(existing_case)
        db.flush()
        _create_quote(db, tid, customer.id, "D999004")
        db.commit()

        result = import_cosium_quotes_as_devis(db, tid, user_id=1)
        assert result["imported"] == 1

        devis = db.query(Devis).filter(Devis.numero == "D999004").first()
        assert devis.case_id == existing_case.id


class TestDevisImportResteACharge:
    """Test 4: Import calculates reste_a_charge correctly."""

    def test_rac_calculation(self, db, default_tenant):
        tid = default_tenant.id
        customer = _create_customer(db, tid)
        _create_quote(db, tid, customer.id, "D999005", 1000.0, 50.0, 700.0)
        db.commit()

        import_cosium_quotes_as_devis(db, tid, user_id=1)

        devis = db.query(Devis).filter(Devis.numero == "D999005").first()
        assert devis is not None
        assert float(devis.reste_a_charge) == 250.0
        assert float(devis.montant_ttc) == 1000.0
        assert float(devis.part_secu) == 50.0
        assert float(devis.part_mutuelle) == 700.0

    def test_rac_never_negative(self, db, default_tenant):
        tid = default_tenant.id
        customer = _create_customer(db, tid)
        # secu + mutuelle > TTC
        _create_quote(db, tid, customer.id, "D999006", 500.0, 300.0, 400.0)
        db.commit()

        import_cosium_quotes_as_devis(db, tid, user_id=1)

        devis = db.query(Devis).filter(Devis.numero == "D999006").first()
        assert float(devis.reste_a_charge) == 0.0


class TestDevisImportSkipsNoCustomer:
    """Test 5: Import skips quotes without customer_id."""

    def test_no_customer(self, db, default_tenant):
        tid = default_tenant.id
        _create_quote(db, tid, None, "D999007")
        db.commit()

        result = import_cosium_quotes_as_devis(db, tid, user_id=1)

        assert result["no_customer"] == 1
        assert result["imported"] == 0
        assert db.query(Devis).filter(Devis.numero == "D999007").count() == 0
