"""Smoke tests pour les 7 services critiques restants (P1).

Services couverts : marketing_service, consolidation_service,
client_360_finance, client_360_documents, batch_processing_service,
erp_sync_invoices, erp_sync_payments.

Objectif : happy path + edge case + isolation tenant quand pertinent.
Pas de validation exhaustive — on vérifie juste que le service ne plante pas
sur des inputs basiques et gère les cas limites connus.
"""

from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError


def _tenant_id(db) -> int:
    from app.models import Tenant

    return db.query(Tenant).filter(Tenant.slug == "test-magasin").first().id


def _other_tenant_id(db, tenant_id: int) -> int:
    """Crée et renvoie un second tenant dans la même organisation."""
    from app.models import Tenant

    primary = db.get(Tenant, tenant_id)
    other = Tenant(organization_id=primary.organization_id, name="Other", slug="other-smoke")
    db.add(other)
    db.flush()
    return other.id


# ---------------------------------------------------------------------------
# marketing_service
# ---------------------------------------------------------------------------


class TestMarketingService:
    def test_list_segments_empty(self, db):
        from app.services import marketing_service

        assert marketing_service.list_segments(db, _tenant_id(db)) == []

    def test_create_segment_happy_path(self, db, seed_user):
        from app.domain.schemas.marketing import SegmentCreate
        from app.services import marketing_service

        tid = _tenant_id(db)
        payload = SegmentCreate(name="VIP", description="Top clients", rules_json={"all": True})
        seg = marketing_service.create_segment(db, tid, payload, seed_user.id)

        assert seg.id is not None
        assert seg.name == "VIP"
        assert seg.member_count >= 0  # tenant vierge => 0

    def test_refresh_segment_unknown_raises(self, db):
        from app.services import marketing_service

        with pytest.raises(NotFoundError):
            marketing_service.refresh_segment(db, _tenant_id(db), segment_id=99999)

    def test_list_campaigns_empty(self, db):
        from app.services import marketing_service

        assert marketing_service.list_campaigns(db, _tenant_id(db)) == []


# ---------------------------------------------------------------------------
# consolidation_service
# ---------------------------------------------------------------------------


class TestConsolidationService:
    def test_consolidate_unknown_customer_returns_empty_profile(self, db):
        """Customer inexistant : profil vide, score 0, champs requis manquants."""
        from app.services import consolidation_service

        profile = consolidation_service.consolidate_client_for_pec(
            db, tenant_id=_tenant_id(db), customer_id=99999,
        )
        assert profile.score_completude == 0
        assert len(profile.champs_manquants) > 0
        assert profile.sources_utilisees == []

    def test_consolidate_minimal_customer(self, db, seed_user):
        """Customer sans prescription/devis/mutuelle : profil partiellement rempli."""
        from app.domain.schemas.clients import ClientCreate
        from app.services import client_service, consolidation_service

        tid = _tenant_id(db)
        client = client_service.create_client(
            db, tid, ClientCreate(first_name="Jean", last_name="Test"), seed_user.id,
        )
        profile = consolidation_service.consolidate_client_for_pec(
            db, tenant_id=tid, customer_id=client.id,
        )
        assert "cosium_client" in profile.sources_utilisees
        # Champs de base remplis via la fiche client
        assert profile.champs_manquants is not None


# ---------------------------------------------------------------------------
# client_360_finance
# ---------------------------------------------------------------------------


class TestClient360Finance:
    def test_aggregate_empty_cases(self):
        from app.services import client_360_finance

        result = client_360_finance.aggregate_case_financials([])
        assert result["devis"] == []
        assert result["factures"] == []
        assert result["paiements"] == []
        assert result["pec"] == []
        assert result["total_facture"] == 0.0
        assert result["total_paye"] == 0.0

    def test_build_financial_summary_zero_facture(self):
        from app.services import client_360_finance

        summary = client_360_finance.build_financial_summary(0.0, 0.0)
        assert summary.total_facture == 0.0
        assert summary.reste_du == 0.0
        assert summary.taux_recouvrement == 0

    def test_build_financial_summary_with_amounts(self):
        from app.services import client_360_finance

        summary = client_360_finance.build_financial_summary(200.0, 150.0)
        assert summary.total_facture == 200.0
        assert summary.total_paye == 150.0
        assert summary.reste_du == 50.0
        assert summary.taux_recouvrement == 75.0

    def test_compute_total_ca_cosium_filters_types(self):
        from app.services import client_360_finance

        invoices = [
            SimpleNamespace(type="INVOICE", total_ti=100.0),
            SimpleNamespace(type="CREDIT_NOTE", total_ti=-20.0),
            SimpleNamespace(type="QUOTE", total_ti=500.0),  # exclu
        ]
        total = client_360_finance.compute_total_ca_cosium(invoices)
        assert total == 80.0  # 100 - 20, quote ignoré

    def test_fetch_cosium_invoices_empty(self, db):
        from app.services import client_360_finance

        invoices, raw = client_360_finance.fetch_cosium_invoices(
            db, tenant_id=_tenant_id(db), client_id=1, client_full_name="Unknown",
        )
        assert invoices == []
        assert raw == []

    def test_fetch_cosium_invoices_tenant_isolation(self, db):
        """Un invoice d'un autre tenant ne doit pas remonter."""
        from app.models.cosium_data import CosiumInvoice
        from app.services import client_360_finance

        tid = _tenant_id(db)
        other = _other_tenant_id(db, tid)
        db.add(CosiumInvoice(
            tenant_id=other, cosium_id=42, invoice_number="X1",
            type="INVOICE", customer_name="JEAN DUPONT",
            total_ti=100.0, outstanding_balance=0.0,
        ))
        db.commit()

        invoices, _ = client_360_finance.fetch_cosium_invoices(
            db, tenant_id=tid, client_id=1, client_full_name="Jean Dupont",
        )
        assert invoices == []

    def test_build_prescription_warning_empty(self):
        from app.services import client_360_finance

        assert client_360_finance.build_prescription_warning([]) is None


# ---------------------------------------------------------------------------
# client_360_documents
# ---------------------------------------------------------------------------


class TestClient360Documents:
    def test_build_prescriptions_empty(self, db):
        from app.services import client_360_documents

        out, raw = client_360_documents.build_prescriptions(
            db, tenant_id=_tenant_id(db), client_id=1, cosium_id=None,
        )
        assert out == []
        assert raw == []

    def test_build_correction_actuelle_empty(self):
        from app.services import client_360_documents

        assert client_360_documents.build_correction_actuelle([]) is None

    def test_build_equipments_empty(self):
        from app.services import client_360_documents

        assert client_360_documents.build_equipments([]) == []

    def test_build_equipments_malformed_json_skipped(self):
        """JSON invalide : log un warning mais ne plante pas."""
        from app.services import client_360_documents

        rx = SimpleNamespace(id=1, prescription_date=None, spectacles_json="{not-json")
        assert client_360_documents.build_equipments([rx]) == []

    def test_build_cosium_payments_empty_ids(self, db):
        from app.services import client_360_documents

        assert client_360_documents.build_cosium_payments(
            db, tenant_id=_tenant_id(db), invoice_cosium_ids=[],
        ) == []

    def test_get_last_visit_date_from_calendar(self):
        from app.services import client_360_documents

        ev = SimpleNamespace(canceled=False, start_date=date(2026, 4, 10))
        result = client_360_documents.get_last_visit_date([ev], [])
        assert "2026-04-10" in result

    def test_get_last_visit_date_fallback_to_invoice(self):
        from app.services import client_360_documents

        inv = SimpleNamespace(invoice_date=date(2026, 1, 15))
        result = client_360_documents.get_last_visit_date([], [inv])
        assert "2026-01-15" in result

    def test_get_last_visit_date_none_when_no_data(self):
        from app.services import client_360_documents

        assert client_360_documents.get_last_visit_date([], []) is None

    def test_get_customer_tags_no_cosium_id(self, db):
        from app.services import client_360_documents

        assert client_360_documents.get_customer_tags(db, _tenant_id(db), None) == []

    def test_build_ocr_data_no_cosium_id(self, db):
        from app.services import client_360_documents

        assert client_360_documents.build_ocr_data(
            db, tenant_id=_tenant_id(db), client_id=1, cosium_id=None, prescriptions_raw=[],
        ) is None


# ---------------------------------------------------------------------------
# batch_processing_service
# ---------------------------------------------------------------------------


class TestBatchProcessingService:
    def test_process_unknown_batch_raises(self, db, seed_user):
        from app.services import batch_processing_service

        with pytest.raises(NotFoundError):
            batch_processing_service.process_batch(
                db, _tenant_id(db), batch_id=99999, user_id=seed_user.id,
            )

    def test_prepare_batch_pec_unknown_raises(self, db, seed_user):
        from app.services import batch_processing_service

        with pytest.raises(NotFoundError):
            batch_processing_service.prepare_batch_pec(
                db, _tenant_id(db), batch_id=99999, user_id=seed_user.id,
            )

    def test_get_batch_summary_enriched_unknown_raises(self, db):
        from app.services import batch_processing_service

        with pytest.raises(NotFoundError):
            batch_processing_service.get_batch_summary_enriched(
                db, _tenant_id(db), batch_id=99999,
            )


# ---------------------------------------------------------------------------
# erp_sync_invoices
# ---------------------------------------------------------------------------


class TestErpSyncInvoices:
    def test_sync_invoices_empty_connector_returns_zero_counts(self, db, seed_user, monkeypatch):
        """Connector qui renvoie 0 facture : service ne plante pas, counts à 0."""
        from app.services import erp_sync_invoices

        tid = _tenant_id(db)

        fake_connector = MagicMock()
        fake_connector.get_invoices.return_value = []
        fake_connector.get_invoices_by_date_range.return_value = []

        from app.models import Tenant
        fake_tenant = db.get(Tenant, tid)

        monkeypatch.setattr(
            erp_sync_invoices, "_get_connector_for_tenant",
            lambda db, tid: (fake_connector, fake_tenant),
        )
        monkeypatch.setattr(erp_sync_invoices, "_authenticate_connector", lambda *a, **k: None)

        result = erp_sync_invoices.sync_invoices(db, tid, seed_user.id, full=True)
        assert result["created"] == 0
        assert result["updated"] == 0


# ---------------------------------------------------------------------------
# erp_sync_payments
# ---------------------------------------------------------------------------


class TestErpSyncPayments:
    def test_sync_payments_non_cosium_connector_returns_note(self, db, seed_user, monkeypatch):
        """Connector non-Cosium : service renvoie une note sans planter."""
        from app.services import erp_sync_payments

        tid = _tenant_id(db)

        # MagicMock n'est pas une CosiumConnector -> branche "not supported"
        fake_connector = MagicMock()
        from app.models import Tenant
        fake_tenant = db.get(Tenant, tid)

        monkeypatch.setattr(
            erp_sync_payments, "_get_connector_for_tenant",
            lambda db, tid: (fake_connector, fake_tenant),
        )
        monkeypatch.setattr(erp_sync_payments, "_authenticate_connector", lambda *a, **k: None)

        result = erp_sync_payments.sync_payments(db, tid, seed_user.id, full=True)
        assert result["created"] == 0
        assert "note" in result

    def test_sync_payments_cosium_connector_empty(self, db, seed_user, monkeypatch):
        """Connector Cosium qui renvoie 0 paiements : counts à 0."""
        from app.integrations.cosium.cosium_connector import CosiumConnector
        from app.services import erp_sync_payments

        tid = _tenant_id(db)

        fake_connector = MagicMock(spec=CosiumConnector)
        fake_connector.get_invoice_payments.return_value = []
        from app.models import Tenant
        fake_tenant = db.get(Tenant, tid)

        monkeypatch.setattr(
            erp_sync_payments, "_get_connector_for_tenant",
            lambda db, tid: (fake_connector, fake_tenant),
        )
        monkeypatch.setattr(erp_sync_payments, "_authenticate_connector", lambda *a, **k: None)

        result = erp_sync_payments.sync_payments(db, tid, seed_user.id, full=True)
        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["total"] == 0
