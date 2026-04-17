"""Smoke tests pour services critiques sans coverage dedie.

Objectif : happy path + 1 edge case par service pour garantir que le service
ne plante pas sur des inputs basiques. Pas de verification exhaustive.

Services couverts : analytics_cosium_service, client_merge_service,
pec_consolidation_service (partiel).
"""

from datetime import UTC, datetime

import pytest

from app.core.exceptions import BusinessError, NotFoundError
from app.domain.schemas.clients import ClientCreate, ClientMergeRequest


# ---------------------------------------------------------------------------
# analytics_cosium_service
# ---------------------------------------------------------------------------


class TestAnalyticsCosiumService:
    def test_kpis_empty_tenant_returns_zeros(self, db, default_tenant):
        from app.services import analytics_cosium_service

        kpis = analytics_cosium_service.get_cosium_kpis(db, default_tenant.id)
        assert kpis.total_facture_cosium == 0
        assert kpis.total_outstanding == 0
        assert kpis.invoice_count == 0

    def test_kpis_counts_only_tenant_invoices(self, db, default_tenant):
        """Isolation tenant : invoices d'autres tenants ignorees."""
        from app.models import Tenant
        from app.models.cosium_data import CosiumInvoice
        from app.services import analytics_cosium_service

        # Tenant A : invoice 100 EUR
        db.add(CosiumInvoice(
            tenant_id=default_tenant.id, cosium_id=1, invoice_number="A1",
            type="INVOICE", total_ti=100.0, outstanding_balance=0.0,
        ))
        # Tenant B : invoice 500 EUR (doit etre ignoree)
        other = Tenant(organization_id=default_tenant.organization_id, name="Other", slug="other-tenant")
        db.add(other)
        db.flush()
        db.add(CosiumInvoice(
            tenant_id=other.id, cosium_id=2, invoice_number="B1",
            type="INVOICE", total_ti=500.0, outstanding_balance=0.0,
        ))
        db.commit()

        kpis = analytics_cosium_service.get_cosium_kpis(db, default_tenant.id)
        assert kpis.total_facture_cosium == 100.0
        assert kpis.invoice_count == 1

    def test_counts_empty_returns_zeros(self, db, default_tenant):
        from app.services import analytics_cosium_service

        counts = analytics_cosium_service.get_cosium_counts(db, default_tenant.id)
        assert counts.total_clients == 0
        assert counts.total_rdv == 0
        assert counts.total_prescriptions == 0
        assert counts.total_payments == 0

    def test_ca_par_mois_returns_12_months(self, db, default_tenant):
        """Le retour contient toujours 12 buckets mensuels (avec 0 si pas de donnee)."""
        from app.services import analytics_cosium_service

        result = analytics_cosium_service.get_cosium_ca_par_mois(db, default_tenant.id)
        assert len(result) == 12
        assert all(r.ca >= 0 for r in result)


# ---------------------------------------------------------------------------
# client_merge_service
# ---------------------------------------------------------------------------


class TestClientMergeService:
    def test_merge_same_client_rejected(self, db, seed_user):
        from app.services import client_merge_service, client_service

        payload = ClientCreate(first_name="A", last_name="B")
        created = client_service.create_client(db, _tenant_id(db), payload, seed_user.id)

        with pytest.raises(BusinessError) as exc:
            client_merge_service.merge_clients(
                db, _tenant_id(db), keep_id=created.id, merge_id=created.id, user_id=seed_user.id,
            )
        assert exc.value.code == "MERGE_SAME_CLIENT"

    def test_merge_nonexistent_keep_raises_not_found(self, db, seed_user):
        from app.services import client_merge_service

        with pytest.raises(NotFoundError):
            client_merge_service.merge_clients(
                db, _tenant_id(db), keep_id=99999, merge_id=99998, user_id=seed_user.id,
            )

    def test_merge_fills_empty_fields_from_source(self, db, seed_user):
        from app.services import client_merge_service, client_service

        tid = _tenant_id(db)
        # keep : pas d'email, pas de phone
        keep = client_service.create_client(db, tid, ClientCreate(first_name="Keep", last_name="X"), seed_user.id)
        # merge : a email et phone
        merge = client_service.create_client(
            db, tid,
            ClientCreate(first_name="Merge", last_name="X", email="m@x.fr", phone="0600000000"),
            seed_user.id,
        )

        result = client_merge_service.merge_clients(
            db, tid, keep_id=keep.id, merge_id=merge.id, user_id=seed_user.id,
        )
        assert "email" in result.fields_filled
        assert "phone" in result.fields_filled

        # keep a recupere les champs
        from app.models import Customer

        k = db.get(Customer, keep.id)
        assert k.email == "m@x.fr"
        assert k.phone == "0600000000"

        # merge est soft-deleted
        m = db.get(Customer, merge.id)
        assert m.deleted_at is not None


# ---------------------------------------------------------------------------
# pec_consolidation_service (re-exports via pec_preparation_service testes ailleurs)
# ---------------------------------------------------------------------------


class TestPecConsolidationService:
    def test_correct_field_raises_on_unknown_preparation(self, db):
        from app.services import pec_consolidation_service

        with pytest.raises(NotFoundError):
            pec_consolidation_service.correct_field(
                db, tenant_id=_tenant_id(db), preparation_id=99999,
                field_name="last_name", new_value="X", corrected_by=1,
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tenant_id(db) -> int:
    from app.models import Tenant

    return db.query(Tenant).filter(Tenant.slug == "test-magasin").first().id


# Helper pour eviter warnings datetime UTC non utilises
_ = datetime.now(UTC)
_ = ClientMergeRequest
