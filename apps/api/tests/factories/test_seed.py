"""Smoke test pour le factory de seed demo."""

from app.models import (
    BankTransaction,
    Campaign,
    Case,
    Customer,
    Devis,
    Facture,
    PayerOrganization,
    PecRequest,
    Reminder,
)
from tests.factories import seed_demo_data
from tests.factories.seed import seed_demo_data as seed_demo_data_explicit


def test_seed_demo_data_creates_full_dataset(db):
    stats = seed_demo_data(db)

    assert stats["status"] != "skipped" if "status" in stats else True
    assert stats["clients"] == 50
    assert stats["cases"] == 30
    assert 0 < stats["devis"] <= 15
    assert stats["bank_transactions"] == 25
    assert stats["campaigns"] == 1

    assert db.query(Customer).count() >= 50
    assert db.query(Case).count() >= 30
    assert db.query(Devis).count() >= stats["devis"]
    assert db.query(Facture).count() == stats["factures"]
    assert db.query(PayerOrganization).filter_by(code="MGEN").count() == 1
    assert db.query(BankTransaction).count() == 25
    assert db.query(Campaign).count() == 1
    if stats["pec"]:
        assert db.query(PecRequest).count() == stats["pec"]
    if stats["factures"]:
        assert db.query(Reminder).count() <= 5


def test_seed_demo_data_skips_when_data_exists(db):
    seed_demo_data(db)
    second = seed_demo_data(db)
    assert second.get("status") == "skipped"


def test_public_export_matches_module():
    assert seed_demo_data is seed_demo_data_explicit
