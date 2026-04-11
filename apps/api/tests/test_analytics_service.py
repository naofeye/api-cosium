"""Unit tests for analytics_service — direct service function calls."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Case, Customer, Devis, Facture, Payment, Tenant
from app.services import analytics_service


def _tenant_id(db: Session) -> int:
    return db.query(Tenant).filter(Tenant.slug == "test-magasin").first().id


def _seed_customer_case(db: Session, tenant_id: int) -> tuple[int, int]:
    c = Customer(tenant_id=tenant_id, first_name="Test", last_name="Client")
    db.add(c)
    db.flush()
    case = Case(tenant_id=tenant_id, customer_id=c.id, status="draft")
    db.add(case)
    db.flush()
    return c.id, case.id


class TestFinancialKPIs:
    def test_no_data_returns_all_zeros(self, db, seed_user):
        tid = _tenant_id(db)
        result = analytics_service.get_financial_kpis(db, tid)

        assert result.ca_total == 0
        assert result.montant_facture == 0
        assert result.montant_encaisse == 0
        assert result.reste_a_encaisser == 0
        assert result.taux_recouvrement == 0

    def test_with_data_calculates_taux_recouvrement(self, db, seed_user):
        tid = _tenant_id(db)
        _, case_id = _seed_customer_case(db, tid)

        # Create a facture
        devis = Devis(tenant_id=tid, case_id=case_id, numero="DEV-TEST-001", status="signe")
        db.add(devis)
        db.flush()
        facture = Facture(
            tenant_id=tid, case_id=case_id, devis_id=devis.id,
            numero="FAC-TEST-001", montant_ht=100, tva=20, montant_ttc=120,
        )
        db.add(facture)
        db.flush()

        # Create payments: 80 paid out of 120 due
        payment = Payment(
            tenant_id=tid, case_id=case_id, payer_type="client",
            amount_due=120, amount_paid=80, status="partial",
        )
        db.add(payment)
        db.commit()

        result = analytics_service.get_financial_kpis(db, tid)
        assert result.montant_facture == 120.0
        assert result.montant_encaisse == 80.0
        # taux_recouvrement = 80/120 * 100 = 66.7%
        assert result.taux_recouvrement == 66.7


class TestOperationalKPIs:
    def test_dossiers_count_correct(self, db, seed_user):
        tid = _tenant_id(db)
        # Create 3 cases
        for _ in range(3):
            _seed_customer_case(db, tid)
        db.commit()

        result = analytics_service.get_operational_kpis(db, tid)
        assert result.dossiers_en_cours == 3


class TestCommercialKPIs:
    def test_taux_conversion_zero_if_no_devis(self, db, seed_user):
        tid = _tenant_id(db)
        result = analytics_service.get_commercial_kpis(db, tid)

        assert result.taux_conversion == 0
        assert result.devis_en_cours == 0
        assert result.devis_signes == 0
        assert result.panier_moyen == 0


class TestAgingBalance:
    def test_buckets_with_correct_totals(self, db, seed_user):
        tid = _tenant_id(db)
        _, case_id = _seed_customer_case(db, tid)

        now = datetime.now(UTC).replace(tzinfo=None)

        # Payment created 10 days ago (0-30j bucket), 50 remaining
        p1 = Payment(
            tenant_id=tid, case_id=case_id, payer_type="client",
            amount_due=100, amount_paid=50, status="partial",
            created_at=now - timedelta(days=10),
        )
        # Payment created 45 days ago (30-60j bucket), 200 remaining
        p2 = Payment(
            tenant_id=tid, case_id=case_id, payer_type="mutuelle",
            amount_due=200, amount_paid=0, status="pending",
            created_at=now - timedelta(days=45),
        )
        db.add_all([p1, p2])
        db.commit()

        result = analytics_service.get_aging_balance(db, tid)
        assert len(result.buckets) == 4

        bucket_0_30 = next(b for b in result.buckets if b.tranche == "0-30j")
        bucket_30_60 = next(b for b in result.buckets if b.tranche == "30-60j")

        assert bucket_0_30.client == 50.0
        assert bucket_30_60.mutuelle == 200.0
        assert result.total == 250.0
