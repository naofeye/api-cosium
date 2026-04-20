"""Tests for client_merge_service — deduplication and merge logic."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import BusinessError, NotFoundError
from app.models.case import Case
from app.models.client import Customer
from app.models.client_mutuelle import ClientMutuelle
from app.models.cosium_data import (
    CosiumDocument,
    CosiumInvoice,
    CosiumPayment,
    CosiumPrescription,
)
from app.services import client_merge_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_customer(db, tenant_id: int, first_name: str = "Jean", last_name: str = "Dupont", **kwargs) -> Customer:
    """Insert a Customer directly (bypassing client_repo field whitelist for test flexibility)."""
    c = Customer(tenant_id=tenant_id, first_name=first_name, last_name=last_name, **kwargs)
    db.add(c)
    db.flush()
    db.refresh(c)
    return c


def _make_case(db, tenant_id: int, customer_id: int) -> Case:
    case = Case(tenant_id=tenant_id, customer_id=customer_id, status="draft")
    db.add(case)
    db.flush()
    db.refresh(case)
    return case


# ---------------------------------------------------------------------------
# find_duplicates
# ---------------------------------------------------------------------------

class TestFindDuplicates:
    def test_no_duplicates_returns_empty(self, db, default_tenant):
        _make_customer(db, default_tenant.id, "Jean", "Dupont")
        db.commit()

        result = client_merge_service.find_duplicates(db, default_tenant.id)
        assert result == []

    def test_detects_duplicate_by_name(self, db, default_tenant):
        _make_customer(db, default_tenant.id, "Jean", "Dupont")
        _make_customer(db, default_tenant.id, "Jean", "Dupont")
        db.commit()

        result = client_merge_service.find_duplicates(db, default_tenant.id)
        assert len(result) == 1
        assert result[0].count == 2
        assert len(result[0].clients) == 2

    def test_case_insensitive_match(self, db, default_tenant):
        _make_customer(db, default_tenant.id, "JEAN", "DUPONT")
        _make_customer(db, default_tenant.id, "jean", "dupont")
        db.commit()

        result = client_merge_service.find_duplicates(db, default_tenant.id)
        assert len(result) == 1

    def test_soft_deleted_clients_excluded(self, db, default_tenant):
        from datetime import UTC, datetime

        c1 = _make_customer(db, default_tenant.id, "Jean", "Martin")
        c2 = _make_customer(db, default_tenant.id, "Jean", "Martin")
        c2.deleted_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()

        result = client_merge_service.find_duplicates(db, default_tenant.id)
        # Only one active -> no duplicate group
        assert result == []

    def test_different_tenants_not_mixed(self, db, default_tenant):
        from app.models import Organization, Tenant

        org2 = Organization(name="Org2", slug="org2", plan="solo")
        db.add(org2)
        db.flush()
        tenant2 = Tenant(organization_id=org2.id, name="Magasin2", slug="mag2")
        db.add(tenant2)
        db.flush()

        _make_customer(db, default_tenant.id, "Alice", "Doe")
        _make_customer(db, tenant2.id, "Alice", "Doe")
        db.commit()

        result = client_merge_service.find_duplicates(db, default_tenant.id)
        assert result == []


# ---------------------------------------------------------------------------
# merge_clients — happy path
# ---------------------------------------------------------------------------

class TestMergeClientsHappyPath:
    @patch("app.services.audit_service.log_action")
    def test_merge_returns_result(self, mock_audit, db, default_tenant):
        keep = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        merge = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        db.commit()

        result = client_merge_service.merge_clients(
            db, default_tenant.id, keep.id, merge.id, user_id=1
        )

        assert result.kept_client.id == keep.id
        assert result.merged_client_deleted is True

    @patch("app.services.audit_service.log_action")
    def test_merge_transfers_cases(self, mock_audit, db, default_tenant):
        keep = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        merge = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        case1 = _make_case(db, default_tenant.id, merge.id)
        case2 = _make_case(db, default_tenant.id, merge.id)
        db.commit()

        result = client_merge_service.merge_clients(
            db, default_tenant.id, keep.id, merge.id, user_id=1
        )

        assert result.cases_transferred == 2

        db.refresh(case1)
        db.refresh(case2)
        assert case1.customer_id == keep.id
        assert case2.customer_id == keep.id

    @patch("app.services.audit_service.log_action")
    def test_merge_preserves_existing_cases_on_keep_client(self, mock_audit, db, default_tenant):
        keep = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        merge = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        _make_case(db, default_tenant.id, keep.id)   # pre-existing on keep
        _make_case(db, default_tenant.id, merge.id)  # to be transferred
        db.commit()

        result = client_merge_service.merge_clients(
            db, default_tenant.id, keep.id, merge.id, user_id=1
        )

        # Only merge's case is transferred
        assert result.cases_transferred == 1

        from sqlalchemy import select
        total_cases = db.scalars(
            select(Case).where(Case.customer_id == keep.id, Case.tenant_id == default_tenant.id)
        ).all()
        assert len(total_cases) == 2

    @patch("app.services.audit_service.log_action")
    def test_merge_soft_deletes_secondary_client(self, mock_audit, db, default_tenant):
        keep = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        merge = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        db.commit()

        client_merge_service.merge_clients(
            db, default_tenant.id, keep.id, merge.id, user_id=1
        )

        db.refresh(merge)
        assert merge.deleted_at is not None

    @patch("app.services.audit_service.log_action")
    def test_merge_keep_client_not_deleted(self, mock_audit, db, default_tenant):
        keep = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        merge = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        db.commit()

        client_merge_service.merge_clients(
            db, default_tenant.id, keep.id, merge.id, user_id=1
        )

        db.refresh(keep)
        assert keep.deleted_at is None

    @patch("app.services.audit_service.log_action")
    def test_merge_fills_empty_fields_from_secondary(self, mock_audit, db, default_tenant):
        keep = _make_customer(db, default_tenant.id, "Jean", "Dupont", phone=None, email=None)
        merge = _make_customer(
            db, default_tenant.id, "Jean", "Dupont",
            phone="0612345678", email="jean@example.com"
        )
        db.commit()

        result = client_merge_service.merge_clients(
            db, default_tenant.id, keep.id, merge.id, user_id=1
        )

        assert "phone" in result.fields_filled
        assert "email" in result.fields_filled
        db.refresh(keep)
        assert keep.phone == "0612345678"
        assert keep.email == "jean@example.com"

    @patch("app.services.audit_service.log_action")
    def test_merge_does_not_overwrite_existing_fields(self, mock_audit, db, default_tenant):
        keep = _make_customer(db, default_tenant.id, "Jean", "Dupont", phone="0611111111")
        merge = _make_customer(db, default_tenant.id, "Jean", "Dupont", phone="0622222222")
        db.commit()

        result = client_merge_service.merge_clients(
            db, default_tenant.id, keep.id, merge.id, user_id=1
        )

        assert "phone" not in result.fields_filled
        db.refresh(keep)
        assert keep.phone == "0611111111"

    @patch("app.services.audit_service.log_action")
    def test_merge_transfers_client_mutuelles(self, mock_audit, db, default_tenant):
        keep = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        merge = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        mut = ClientMutuelle(
            tenant_id=default_tenant.id,
            customer_id=merge.id,
            mutuelle_name="MGEN",
            source="manual",
            confidence=1.0,
        )
        db.add(mut)
        db.commit()

        client_merge_service.merge_clients(
            db, default_tenant.id, keep.id, merge.id, user_id=1
        )

        db.refresh(mut)
        assert mut.customer_id == keep.id

    @patch("app.services.audit_service.log_action")
    def test_merge_transfers_cosium_invoices(self, mock_audit, db, default_tenant):
        keep = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        merge = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        invoice = CosiumInvoice(
            tenant_id=default_tenant.id,
            cosium_id=9001,
            invoice_number="INV-001",
            customer_name="Jean Dupont",
            customer_id=merge.id,
        )
        db.add(invoice)
        db.commit()

        result = client_merge_service.merge_clients(
            db, default_tenant.id, keep.id, merge.id, user_id=1
        )

        db.refresh(invoice)
        assert invoice.customer_id == keep.id
        assert result.cosium_data_transferred >= 1

    @patch("app.services.audit_service.log_action")
    def test_merge_transfers_cosium_payments(self, mock_audit, db, default_tenant):
        keep = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        merge = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        payment = CosiumPayment(
            tenant_id=default_tenant.id,
            cosium_id=7001,
            customer_id=merge.id,
            amount=150.0,
        )
        db.add(payment)
        db.commit()

        result = client_merge_service.merge_clients(
            db, default_tenant.id, keep.id, merge.id, user_id=1
        )

        db.refresh(payment)
        assert payment.customer_id == keep.id
        assert result.cosium_data_transferred >= 1

    @patch("app.services.audit_service.log_action")
    def test_merge_transfers_cosium_documents(self, mock_audit, db, default_tenant):
        keep = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        merge = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        doc = CosiumDocument(
            tenant_id=default_tenant.id,
            customer_cosium_id=42,
            customer_id=merge.id,
            cosium_document_id=1001,
        )
        db.add(doc)
        db.commit()

        result = client_merge_service.merge_clients(
            db, default_tenant.id, keep.id, merge.id, user_id=1
        )

        db.refresh(doc)
        assert doc.customer_id == keep.id
        assert result.cosium_data_transferred >= 1

    @patch("app.services.audit_service.log_action")
    def test_merge_calls_audit_log(self, mock_audit, db, default_tenant):
        keep = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        merge = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        db.commit()

        client_merge_service.merge_clients(
            db, default_tenant.id, keep.id, merge.id, user_id=99
        )

        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args
        # audit_service.log_action(db, tenant_id, user_id, "merge", "client", keep_id, new_value=...)
        args = call_kwargs.args
        assert args[2] == 99          # user_id
        assert args[3] == "merge"     # action
        assert args[4] == "client"    # entity_type
        assert args[5] == keep.id     # entity_id


# ---------------------------------------------------------------------------
# merge_clients — error cases
# ---------------------------------------------------------------------------

class TestMergeClientsErrors:
    def test_merge_same_client_raises_business_error(self, db, default_tenant):
        keep = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        db.commit()

        with pytest.raises(BusinessError) as exc_info:
            client_merge_service.merge_clients(
                db, default_tenant.id, keep.id, keep.id, user_id=1
            )
        assert exc_info.value.code == "MERGE_SAME_CLIENT"

    def test_merge_unknown_keep_id_raises_not_found(self, db, default_tenant):
        merge = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        db.commit()

        with pytest.raises(NotFoundError):
            client_merge_service.merge_clients(
                db, default_tenant.id, 99999, merge.id, user_id=1
            )

    def test_merge_unknown_merge_id_raises_not_found(self, db, default_tenant):
        keep = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        db.commit()

        with pytest.raises(NotFoundError):
            client_merge_service.merge_clients(
                db, default_tenant.id, keep.id, 99999, user_id=1
            )

    def test_cannot_merge_clients_from_different_tenants(self, db, default_tenant):
        """A client belonging to another tenant is invisible — raises NotFoundError."""
        from app.models import Organization, Tenant

        org2 = Organization(name="OtherOrg", slug="other-org", plan="solo")
        db.add(org2)
        db.flush()
        tenant2 = Tenant(organization_id=org2.id, name="OtherMag", slug="other-mag")
        db.add(tenant2)
        db.flush()

        keep = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        merge_other = _make_customer(db, tenant2.id, "Jean", "Dupont")
        db.commit()

        # merge_id belongs to tenant2, not visible from default_tenant
        with pytest.raises(NotFoundError):
            client_merge_service.merge_clients(
                db, default_tenant.id, keep.id, merge_other.id, user_id=1
            )

    def test_cannot_use_deleted_keep_client(self, db, default_tenant):
        from datetime import UTC, datetime

        keep = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        merge = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        keep.deleted_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()

        with pytest.raises(NotFoundError):
            client_merge_service.merge_clients(
                db, default_tenant.id, keep.id, merge.id, user_id=1
            )

    def test_cannot_use_deleted_merge_client(self, db, default_tenant):
        from datetime import UTC, datetime

        keep = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        merge = _make_customer(db, default_tenant.id, "Jean", "Dupont")
        merge.deleted_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()

        with pytest.raises(NotFoundError):
            client_merge_service.merge_clients(
                db, default_tenant.id, keep.id, merge.id, user_id=1
            )


# ---------------------------------------------------------------------------
# merge_clients — zero-data edge cases
# ---------------------------------------------------------------------------

class TestMergeClientsEdgeCases:
    @patch("app.services.audit_service.log_action")
    def test_merge_with_no_cases_returns_zero(self, mock_audit, db, default_tenant):
        keep = _make_customer(db, default_tenant.id, "Alice", "Martin")
        merge = _make_customer(db, default_tenant.id, "Alice", "Martin")
        db.commit()

        result = client_merge_service.merge_clients(
            db, default_tenant.id, keep.id, merge.id, user_id=1
        )

        assert result.cases_transferred == 0
        assert result.pec_transferred == 0

    @patch("app.services.audit_service.log_action")
    def test_merge_with_no_cosium_data_returns_zero(self, mock_audit, db, default_tenant):
        keep = _make_customer(db, default_tenant.id, "Alice", "Martin")
        merge = _make_customer(db, default_tenant.id, "Alice", "Martin")
        db.commit()

        result = client_merge_service.merge_clients(
            db, default_tenant.id, keep.id, merge.id, user_id=1
        )

        assert result.cosium_data_transferred == 0

    @patch("app.services.audit_service.log_action")
    def test_merge_with_both_fields_empty_fills_from_merge(self, mock_audit, db, default_tenant):
        keep = _make_customer(db, default_tenant.id, "Alice", "Martin", city=None)
        merge = _make_customer(db, default_tenant.id, "Alice", "Martin", city="Paris")
        db.commit()

        result = client_merge_service.merge_clients(
            db, default_tenant.id, keep.id, merge.id, user_id=1
        )

        assert "city" in result.fields_filled
        db.refresh(keep)
        assert keep.city == "Paris"
