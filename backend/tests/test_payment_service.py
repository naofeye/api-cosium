"""Tests unitaires pour payment_service — resume paiements, soldes."""

from sqlalchemy.orm import Session

from app.models import Case, Customer, Payment, Tenant
from app.services import payment_service


def _make_customer(db: Session, tenant_id: int) -> Customer:
    c = Customer(tenant_id=tenant_id, first_name="Pay", last_name="Client")
    db.add(c)
    db.flush()
    return c


def _make_case(db: Session, tenant_id: int, customer_id: int) -> Case:
    case = Case(tenant_id=tenant_id, customer_id=customer_id, status="draft")
    db.add(case)
    db.flush()
    return case


def _add_payment(db: Session, tenant_id: int, case_id: int, payer_type: str,
                 amount_due: float, amount_paid: float, status: str) -> Payment:
    p = Payment(
        tenant_id=tenant_id, case_id=case_id, payer_type=payer_type,
        amount_due=amount_due, amount_paid=amount_paid, status=status,
    )
    db.add(p)
    db.commit()
    return p


class TestGetPaymentSummary:
    """Tests du resume financier des paiements d'un dossier."""

    def test_empty_case_returns_zero_summary(self, db, seed_user):
        """Un dossier sans paiement doit retourner des totaux a zero."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        case = _make_case(db, tenant.id, customer.id)

        summary = payment_service.get_payment_summary(db, tenant.id, case.id)

        assert summary.case_id == case.id
        assert summary.total_due == 0
        assert summary.total_paid == 0
        assert summary.remaining == 0
        assert summary.items == []

    def test_single_payment_fully_paid(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        case = _make_case(db, tenant.id, customer.id)
        _add_payment(db, tenant.id, case.id, "client", 100.0, 100.0, "paid")

        summary = payment_service.get_payment_summary(db, tenant.id, case.id)

        assert summary.total_due == 100.0
        assert summary.total_paid == 100.0
        assert summary.remaining == 0
        assert len(summary.items) == 1

    def test_multiple_payments_partial(self, db, seed_user):
        """Plusieurs paiements avec paiement partiel."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        case = _make_case(db, tenant.id, customer.id)
        _add_payment(db, tenant.id, case.id, "mutuelle", 200.0, 100.0, "partial")
        _add_payment(db, tenant.id, case.id, "client", 50.0, 50.0, "paid")

        summary = payment_service.get_payment_summary(db, tenant.id, case.id)

        assert summary.total_due == 250.0
        assert summary.total_paid == 150.0
        assert summary.remaining == 100.0
        assert len(summary.items) == 2

    def test_summary_items_have_correct_payer_type(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        customer = _make_customer(db, tenant.id)
        case = _make_case(db, tenant.id, customer.id)
        _add_payment(db, tenant.id, case.id, "mutuelle", 300.0, 200.0, "partial")

        summary = payment_service.get_payment_summary(db, tenant.id, case.id)

        assert summary.items[0].payer_type == "mutuelle"
        assert summary.items[0].amount_due == 300.0
        assert summary.items[0].amount_paid == 200.0

    def test_summary_for_nonexistent_case(self, db, seed_user):
        """Un dossier sans paiement retourne un summary vide (pas d'erreur)."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        summary = payment_service.get_payment_summary(db, tenant.id, 99999)

        assert summary.total_due == 0
        assert summary.total_paid == 0
        assert summary.remaining == 0
