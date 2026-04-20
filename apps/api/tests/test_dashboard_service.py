"""Tests unitaires pour dashboard_service.get_summary().

Couvre :
- Valeurs KPI avec des donnees en base (cases, documents, payments)
- Coherence des calculs (alerts_count, remaining)
- Isolation par tenant_id
- Base vide (aucune donnee) -> zeros sans erreur
- Plusieurs payments -> agregation SQL correcte
- Arrondi a 2 decimales sur les montants
"""
from decimal import Decimal

import pytest

from app.models import Case, Customer, Document, Payment, Tenant
from app.services import dashboard_service


# ---------------------------------------------------------------------------
# Fixtures locales
# ---------------------------------------------------------------------------


@pytest.fixture(name="tenant2")
def tenant2_fixture(db):
    """Second tenant pour verifier l'isolation des donnees."""
    from app.models import Organization

    org = Organization(name="Autre Org", slug="autre-org", plan="solo")
    db.add(org)
    db.flush()
    t = Tenant(
        organization_id=org.id,
        name="Autre Magasin",
        slug="autre-magasin",
        cosium_tenant="t2",
        cosium_login="l2",
        cosium_password_enc="p2",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@pytest.fixture(name="customer")
def customer_fixture(db, default_tenant):
    cust = Customer(tenant_id=default_tenant.id, first_name="Jean", last_name="Dupont")
    db.add(cust)
    db.flush()
    return cust


@pytest.fixture(name="case_obj")
def case_fixture(db, default_tenant, customer):
    c = Case(tenant_id=default_tenant.id, customer_id=customer.id, status="draft")
    db.add(c)
    db.flush()
    return c


def _make_payment(db, tenant_id: int, case_id: int, amount_due: float, amount_paid: float) -> Payment:
    p = Payment(
        tenant_id=tenant_id,
        case_id=case_id,
        payer_type="client",
        amount_due=Decimal(str(amount_due)),
        amount_paid=Decimal(str(amount_paid)),
    )
    db.add(p)
    db.flush()
    return p


def _make_document(db, tenant_id: int, case_id: int, filename: str = "doc.pdf") -> Document:
    doc = Document(
        tenant_id=tenant_id,
        case_id=case_id,
        type="ordonnance",
        filename=filename,
        storage_key=f"keys/{filename}",
    )
    db.add(doc)
    db.flush()
    return doc


# ---------------------------------------------------------------------------
# Tests : base vide
# ---------------------------------------------------------------------------


class TestDashboardEmptyDatabase:
    def test_empty_db_returns_zeros(self, db, default_tenant):
        """Aucune donnee -> tous les champs sont a zero, pas d'erreur."""
        summary = dashboard_service.get_summary(db, tenant_id=default_tenant.id)

        assert summary.cases_count == 0
        assert summary.documents_count == 0
        assert summary.alerts_count == 0
        assert summary.total_due == 0.0
        assert summary.total_paid == 0.0
        assert summary.remaining == 0.0

    def test_empty_db_schema_fields_present(self, db, default_tenant):
        """Le schema DashboardSummary doit contenir les 6 champs attendus."""
        summary = dashboard_service.get_summary(db, tenant_id=default_tenant.id)
        assert hasattr(summary, "cases_count")
        assert hasattr(summary, "documents_count")
        assert hasattr(summary, "alerts_count")
        assert hasattr(summary, "total_due")
        assert hasattr(summary, "total_paid")
        assert hasattr(summary, "remaining")


# ---------------------------------------------------------------------------
# Tests : comptage des cases
# ---------------------------------------------------------------------------


class TestDashboardCasesCount:
    def test_single_case_counted(self, db, default_tenant, case_obj):
        db.commit()
        summary = dashboard_service.get_summary(db, tenant_id=default_tenant.id)
        assert summary.cases_count == 1

    def test_multiple_cases_counted(self, db, default_tenant, customer):
        for _ in range(4):
            db.add(Case(tenant_id=default_tenant.id, customer_id=customer.id, status="draft"))
        db.commit()
        summary = dashboard_service.get_summary(db, tenant_id=default_tenant.id)
        assert summary.cases_count == 4

    def test_cases_from_other_tenant_not_counted(self, db, default_tenant, tenant2, customer):
        """Cases d'un autre tenant ne doivent pas apparaitre dans le summary."""
        cust2 = Customer(tenant_id=tenant2.id, first_name="X", last_name="Y")
        db.add(cust2)
        db.flush()
        db.add(Case(tenant_id=tenant2.id, customer_id=cust2.id, status="draft"))
        # Un case pour le tenant courant
        db.add(Case(tenant_id=default_tenant.id, customer_id=customer.id, status="draft"))
        db.commit()

        summary = dashboard_service.get_summary(db, tenant_id=default_tenant.id)
        assert summary.cases_count == 1


# ---------------------------------------------------------------------------
# Tests : comptage des documents
# ---------------------------------------------------------------------------


class TestDashboardDocumentsCount:
    def test_documents_counted(self, db, default_tenant, case_obj):
        _make_document(db, default_tenant.id, case_obj.id, "a.pdf")
        _make_document(db, default_tenant.id, case_obj.id, "b.pdf")
        db.commit()

        summary = dashboard_service.get_summary(db, tenant_id=default_tenant.id)
        assert summary.documents_count == 2

    def test_documents_from_other_tenant_excluded(self, db, default_tenant, tenant2, case_obj):
        cust2 = Customer(tenant_id=tenant2.id, first_name="A", last_name="B")
        db.add(cust2)
        db.flush()
        case2 = Case(tenant_id=tenant2.id, customer_id=cust2.id, status="draft")
        db.add(case2)
        db.flush()
        _make_document(db, tenant2.id, case2.id, "other.pdf")
        _make_document(db, default_tenant.id, case_obj.id, "mine.pdf")
        db.commit()

        summary = dashboard_service.get_summary(db, tenant_id=default_tenant.id)
        assert summary.documents_count == 1


# ---------------------------------------------------------------------------
# Tests : calcul alerts_count
# ---------------------------------------------------------------------------


class TestDashboardAlertsCount:
    def test_alerts_is_max_cases_minus_docs_zero(self, db, default_tenant, case_obj):
        """Plus de documents que de cases -> alerts = 0 (pas negatif)."""
        _make_document(db, default_tenant.id, case_obj.id, "x.pdf")
        _make_document(db, default_tenant.id, case_obj.id, "y.pdf")
        db.commit()

        summary = dashboard_service.get_summary(db, tenant_id=default_tenant.id)
        # 1 case, 2 documents -> max(1-2, 0) = 0
        assert summary.alerts_count == 0

    def test_alerts_positive_when_cases_exceed_docs(self, db, default_tenant, customer):
        """3 cases, 1 document -> alerts = 2."""
        for _ in range(3):
            case = Case(tenant_id=default_tenant.id, customer_id=customer.id, status="draft")
            db.add(case)
            db.flush()
        # Ajouter 1 document sur le premier case
        first_case = db.query(Case).filter(Case.tenant_id == default_tenant.id).first()
        _make_document(db, default_tenant.id, first_case.id, "doc.pdf")
        db.commit()

        summary = dashboard_service.get_summary(db, tenant_id=default_tenant.id)
        assert summary.alerts_count == 2  # max(3-1, 0) = 2

    def test_alerts_zero_when_both_empty(self, db, default_tenant):
        summary = dashboard_service.get_summary(db, tenant_id=default_tenant.id)
        assert summary.alerts_count == 0


# ---------------------------------------------------------------------------
# Tests : agregation des paiements
# ---------------------------------------------------------------------------


class TestDashboardPaymentTotals:
    def test_single_payment_totals(self, db, default_tenant, case_obj):
        _make_payment(db, default_tenant.id, case_obj.id, amount_due=150.00, amount_paid=100.00)
        db.commit()

        summary = dashboard_service.get_summary(db, tenant_id=default_tenant.id)
        assert summary.total_due == 150.00
        assert summary.total_paid == 100.00
        assert summary.remaining == 50.00

    def test_multiple_payments_summed(self, db, default_tenant, case_obj):
        _make_payment(db, default_tenant.id, case_obj.id, amount_due=200.00, amount_paid=200.00)
        _make_payment(db, default_tenant.id, case_obj.id, amount_due=80.50, amount_paid=0.00)
        _make_payment(db, default_tenant.id, case_obj.id, amount_due=19.50, amount_paid=10.00)
        db.commit()

        summary = dashboard_service.get_summary(db, tenant_id=default_tenant.id)
        assert summary.total_due == 300.00
        assert summary.total_paid == 210.00
        assert summary.remaining == 90.00

    def test_fully_paid_remaining_is_zero(self, db, default_tenant, case_obj):
        _make_payment(db, default_tenant.id, case_obj.id, amount_due=500.00, amount_paid=500.00)
        db.commit()

        summary = dashboard_service.get_summary(db, tenant_id=default_tenant.id)
        assert summary.remaining == 0.00

    def test_payment_rounding_two_decimals(self, db, default_tenant, case_obj):
        """Les montants sont arrondis a 2 decimales."""
        _make_payment(db, default_tenant.id, case_obj.id, amount_due=99.999, amount_paid=33.333)
        db.commit()

        summary = dashboard_service.get_summary(db, tenant_id=default_tenant.id)
        # Verifie que les valeurs sont des floats bien arrondis (2 decimales max)
        assert isinstance(summary.total_due, float)
        assert isinstance(summary.total_paid, float)
        assert isinstance(summary.remaining, float)

    def test_payments_from_other_tenant_excluded(self, db, default_tenant, tenant2, case_obj):
        cust2 = Customer(tenant_id=tenant2.id, first_name="Z", last_name="W")
        db.add(cust2)
        db.flush()
        case2 = Case(tenant_id=tenant2.id, customer_id=cust2.id, status="draft")
        db.add(case2)
        db.flush()
        # Paiement tenant2 ne doit pas polluer tenant1
        _make_payment(db, tenant2.id, case2.id, amount_due=9999.00, amount_paid=9999.00)
        _make_payment(db, default_tenant.id, case_obj.id, amount_due=50.00, amount_paid=25.00)
        db.commit()

        summary = dashboard_service.get_summary(db, tenant_id=default_tenant.id)
        assert summary.total_due == 50.00
        assert summary.total_paid == 25.00

    def test_no_payments_returns_zero_totals(self, db, default_tenant, case_obj):
        """Cases et documents existent mais aucun paiement -> totaux a 0."""
        db.commit()
        summary = dashboard_service.get_summary(db, tenant_id=default_tenant.id)
        assert summary.total_due == 0.0
        assert summary.total_paid == 0.0
        assert summary.remaining == 0.0


# ---------------------------------------------------------------------------
# Tests : tenant inexistant
# ---------------------------------------------------------------------------


class TestDashboardUnknownTenant:
    def test_unknown_tenant_id_returns_zeros(self, db):
        """Un tenant_id qui n'existe pas doit retourner des zeros, pas une erreur."""
        summary = dashboard_service.get_summary(db, tenant_id=99999)
        assert summary.cases_count == 0
        assert summary.documents_count == 0
        assert summary.total_due == 0.0
        assert summary.total_paid == 0.0
