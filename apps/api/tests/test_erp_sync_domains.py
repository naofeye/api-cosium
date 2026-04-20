"""Unit tests for domain-specific ERP sync services:

- erp_sync_invoices.sync_invoices
- erp_sync_payments.sync_payments
- erp_sync_prescriptions.sync_prescriptions

All external dependencies (CosiumConnector, auth, audit_service) are mocked.
Tests run purely in-memory against the SQLite test DB from conftest.py.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.integrations.erp_models import ERPInvoice
from app.models.cosium_data import CosiumInvoice, CosiumPayment, CosiumPrescription


# ---------------------------------------------------------------------------
# Factories / helpers
# ---------------------------------------------------------------------------


def _make_erp_invoice(
    erp_id: str = "1001",
    number: str = "F2026-001",
    invoice_date: datetime | None = None,
    total_ttc: float = 450.0,
    customer_erp_id: str = "C001",
    customer_name: str = "DUPONT Jean",
    type: str = "INVOICE",
    settled: bool = False,
    outstanding_balance: float = 450.0,
) -> ERPInvoice:
    return ERPInvoice(
        erp_id=erp_id,
        number=number,
        date=invoice_date or datetime(2026, 3, 15, tzinfo=UTC),
        total_ttc=total_ttc,
        customer_erp_id=customer_erp_id,
        customer_name=customer_name,
        type=type,
        settled=settled,
        outstanding_balance=outstanding_balance,
        share_social_security=50.0,
        share_private_insurance=100.0,
        archived=False,
        site_id=1,
    )


def _make_payment(
    cosium_id: int = 5001,
    invoice_cosium_id: int = 1001,
    amount: float = 300.0,
    type: str = "CB",
    customer_cosium_id: str = "C001",
    issuer_name: str = "DUPONT Jean",
    due_date: str = "2026-03-15T00:00:00.000Z",
) -> dict:
    return {
        "cosium_id": cosium_id,
        "invoice_cosium_id": invoice_cosium_id,
        "amount": amount,
        "original_amount": amount,
        "type": type,
        "payment_type_id": 3,
        "customer_cosium_id": customer_cosium_id,
        "issuer_name": issuer_name,
        "due_date": due_date,
        "bank": "LCL",
        "site_name": "Paris",
        "comment": None,
        "payment_number": "PMT-001",
    }


def _make_prescription(
    cosium_id: int = 7001,
    customer_cosium_id: int = 101,
    sphere_right: float = -1.5,
    sphere_left: float = -1.25,
    prescription_date: str = "2025-11-01",
    file_date: str = "2025-11-05T10:00:00.000Z",
    prescriber_name: str = "Dr. Moreau",
) -> dict:
    return {
        "cosium_id": cosium_id,
        "customer_cosium_id": customer_cosium_id,
        "sphere_right": sphere_right,
        "cylinder_right": -0.5,
        "axis_right": 90,
        "addition_right": None,
        "sphere_left": sphere_left,
        "cylinder_left": -0.25,
        "axis_left": 85,
        "addition_left": None,
        "prescription_date": prescription_date,
        "file_date": file_date,
        "spectacles_json": None,
        "prescriber_name": prescriber_name,
    }


def _mock_connector(
    *,
    invoices: list[ERPInvoice] | None = None,
    payments: list[dict] | None = None,
    prescriptions: list[dict] | None = None,
) -> MagicMock:
    """Build a mock CosiumConnector."""
    connector = MagicMock()
    connector.erp_type = "cosium"
    connector.get_invoices.return_value = invoices or []
    connector.get_invoices_by_date_range.return_value = invoices or []
    connector.get_invoice_payments.return_value = payments or []
    connector.get_optical_prescriptions.return_value = prescriptions or []
    return connector


# Patch targets (module-level constants for readability)
_AUTH_GET = "app.services.erp_sync_invoices._get_connector_for_tenant"
_AUTH_AUTH = "app.services.erp_sync_invoices._authenticate_connector"
_INV_AUDIT = "app.services.erp_sync_invoices.audit_service.log_action"

_PAY_GET = "app.services.erp_sync_payments._get_connector_for_tenant"
_PAY_AUTH = "app.services.erp_sync_payments._authenticate_connector"
_PAY_AUDIT = "app.services.erp_sync_payments.audit_service"

_PRESC_GET = "app.services.erp_sync_prescriptions._get_connector_for_tenant"
_PRESC_AUTH = "app.services.erp_sync_prescriptions._authenticate_connector"
_PRESC_AUDIT = "app.services.erp_sync_prescriptions.audit_service"

# CosiumConnector type-check target (used in payments & prescriptions isinstance guard)
_COSIUM_CONNECTOR_CLASS = "app.services.erp_sync_payments.CosiumConnector"
_COSIUM_CONNECTOR_CLASS_PRESC = "app.services.erp_sync_prescriptions.CosiumConnector"


# ===========================================================================
# INVOICES
# ===========================================================================


class TestSyncInvoicesHappyPath:
    """sync_invoices creates and updates CosiumInvoice rows correctly."""

    def test_creates_new_invoices(self, db, default_tenant):
        connector = _mock_connector(invoices=[_make_erp_invoice()])

        with (
            patch(_AUTH_GET, return_value=(connector, default_tenant)),
            patch(_AUTH_AUTH),
            patch(_INV_AUDIT),
        ):
            from app.services.erp_sync_invoices import sync_invoices

            result = sync_invoices(db, tenant_id=default_tenant.id, user_id=1, full=True)

        assert result["created"] == 1
        assert result["updated"] == 0
        assert result["total"] == 1
        assert result["batch_errors"] == 0

        rows = db.query(CosiumInvoice).filter(CosiumInvoice.tenant_id == default_tenant.id).all()
        assert len(rows) == 1
        assert rows[0].cosium_id == 1001
        assert rows[0].invoice_number == "F2026-001"
        assert rows[0].total_ti == 450.0

    def test_updates_existing_invoice(self, db, default_tenant):
        # Pre-seed an invoice
        existing = CosiumInvoice(
            tenant_id=default_tenant.id,
            cosium_id=1001,
            invoice_number="F2026-001",
            invoice_date=datetime(2026, 3, 15, tzinfo=UTC),
            customer_name="DUPONT Jean",
            type="INVOICE",
            total_ti=300.0,
            outstanding_balance=300.0,
            settled=False,
            archived=False,
        )
        db.add(existing)
        db.commit()

        # ERP now returns updated total
        invoice = _make_erp_invoice(total_ttc=450.0, settled=True, outstanding_balance=0.0)
        connector = _mock_connector(invoices=[invoice])

        with (
            patch(_AUTH_GET, return_value=(connector, default_tenant)),
            patch(_AUTH_AUTH),
            patch(_INV_AUDIT),
        ):
            from app.services.erp_sync_invoices import sync_invoices

            result = sync_invoices(db, tenant_id=default_tenant.id, user_id=1, full=True)

        assert result["created"] == 0
        assert result["updated"] == 1
        db.refresh(existing)
        assert existing.total_ti == 450.0
        assert existing.settled is True
        assert existing.outstanding_balance == 0.0

    def test_multiple_invoices_all_created(self, db, default_tenant):
        invoices = [
            _make_erp_invoice(erp_id=str(i), number=f"F2026-{i:03d}", customer_erp_id=f"C{i:03d}")
            for i in range(1001, 1006)
        ]
        connector = _mock_connector(invoices=invoices)

        with (
            patch(_AUTH_GET, return_value=(connector, default_tenant)),
            patch(_AUTH_AUTH),
            patch(_INV_AUDIT),
        ):
            from app.services.erp_sync_invoices import sync_invoices

            result = sync_invoices(db, tenant_id=default_tenant.id, user_id=1, full=True)

        assert result["created"] == 5
        assert result["total"] == 5

    def test_invoice_date_string_parsed(self, db, default_tenant):
        """ERPInvoice.date as ISO string is correctly parsed to datetime."""
        invoice = ERPInvoice(
            erp_id="2001",
            number="F2026-STR",
            date="2026-03-20T23:00:00.000Z",  # type: ignore[arg-type]
            total_ttc=200.0,
            customer_erp_id="C999",
            customer_name="TEST Client",
        )
        connector = _mock_connector(invoices=[invoice])

        with (
            patch(_AUTH_GET, return_value=(connector, default_tenant)),
            patch(_AUTH_AUTH),
            patch(_INV_AUDIT),
        ):
            from app.services.erp_sync_invoices import sync_invoices

            result = sync_invoices(db, tenant_id=default_tenant.id, user_id=1, full=True)

        assert result["created"] == 1
        row = db.query(CosiumInvoice).filter(CosiumInvoice.cosium_id == 2001).first()
        assert row is not None
        assert row.invoice_date is not None


class TestSyncInvoicesIncrementalMode:
    """sync_invoices uses date-range fetch when existing records are present."""

    def test_incremental_uses_date_range(self, db, default_tenant):
        # Pre-seed an invoice so last_date is set
        existing = CosiumInvoice(
            tenant_id=default_tenant.id,
            cosium_id=999,
            invoice_number="OLD-001",
            invoice_date=datetime(2026, 1, 10, tzinfo=UTC),
            customer_name="Ancien Client",
            type="INVOICE",
            total_ti=100.0,
            outstanding_balance=0.0,
            settled=True,
            archived=False,
        )
        db.add(existing)
        db.commit()

        new_invoice = _make_erp_invoice(erp_id="1002", number="F2026-002")
        connector = _mock_connector(invoices=[new_invoice])

        with (
            patch(_AUTH_GET, return_value=(connector, default_tenant)),
            patch(_AUTH_AUTH),
            patch(_INV_AUDIT),
        ):
            from app.services.erp_sync_invoices import sync_invoices

            result = sync_invoices(db, tenant_id=default_tenant.id, user_id=1, full=False)

        # Incremental path calls get_invoices_by_date_range, not get_invoices
        connector.get_invoices_by_date_range.assert_called_once()
        connector.get_invoices.assert_not_called()
        assert result["created"] == 1

    def test_incremental_date_from_includes_margin(self, db, default_tenant):
        """Incremental sync subtracts INCREMENTAL_MARGIN_DAYS from last invoice date."""
        from app.services.erp_sync_invoices import INCREMENTAL_MARGIN_DAYS

        last_date = datetime(2026, 3, 20, tzinfo=UTC)
        existing = CosiumInvoice(
            tenant_id=default_tenant.id,
            cosium_id=888,
            invoice_number="MARGIN-001",
            invoice_date=last_date,
            customer_name="Client Marge",
            type="INVOICE",
            total_ti=0.0,
            outstanding_balance=0.0,
            settled=True,
            archived=False,
        )
        db.add(existing)
        db.commit()

        connector = _mock_connector(invoices=[])

        with (
            patch(_AUTH_GET, return_value=(connector, default_tenant)),
            patch(_AUTH_AUTH),
            patch(_INV_AUDIT),
        ):
            from app.services.erp_sync_invoices import sync_invoices

            sync_invoices(db, tenant_id=default_tenant.id, user_id=1, full=False)

        args, _ = connector.get_invoices_by_date_range.call_args
        date_from_str = args[0]
        # Expected start = last_date - margin
        expected_from = (last_date - timedelta(days=INCREMENTAL_MARGIN_DAYS)).strftime(
            "%Y-%m-%dT00:00:00.000Z"
        )
        assert date_from_str == expected_from

    def test_full_sync_uses_get_invoices(self, db, default_tenant):
        """full=True always calls get_invoices, regardless of existing records."""
        # Pre-seed to ensure incremental would normally be used
        existing = CosiumInvoice(
            tenant_id=default_tenant.id,
            cosium_id=777,
            invoice_number="PRIOR-001",
            invoice_date=datetime(2026, 2, 1, tzinfo=UTC),
            customer_name="Client",
            type="INVOICE",
            total_ti=0.0,
            outstanding_balance=0.0,
            settled=True,
            archived=False,
        )
        db.add(existing)
        db.commit()

        connector = _mock_connector(invoices=[])

        with (
            patch(_AUTH_GET, return_value=(connector, default_tenant)),
            patch(_AUTH_AUTH),
            patch(_INV_AUDIT),
        ):
            from app.services.erp_sync_invoices import sync_invoices

            sync_invoices(db, tenant_id=default_tenant.id, user_id=1, full=True)

        connector.get_invoices.assert_called_once()
        connector.get_invoices_by_date_range.assert_not_called()

    def test_first_sync_no_existing_records_uses_get_invoices(self, db, default_tenant):
        """When no records exist and full=False, falls back to get_invoices (first sync)."""
        connector = _mock_connector(invoices=[])

        with (
            patch(_AUTH_GET, return_value=(connector, default_tenant)),
            patch(_AUTH_AUTH),
            patch(_INV_AUDIT),
        ):
            from app.services.erp_sync_invoices import sync_invoices

            sync_invoices(db, tenant_id=default_tenant.id, user_id=1, full=False)

        connector.get_invoices.assert_called_once()
        connector.get_invoices_by_date_range.assert_not_called()


class TestSyncInvoicesEmptyERP:
    """sync_invoices handles empty ERP responses gracefully."""

    def test_empty_erp_response_full(self, db, default_tenant):
        connector = _mock_connector(invoices=[])

        with (
            patch(_AUTH_GET, return_value=(connector, default_tenant)),
            patch(_AUTH_AUTH),
            patch(_INV_AUDIT),
        ):
            from app.services.erp_sync_invoices import sync_invoices

            result = sync_invoices(db, tenant_id=default_tenant.id, user_id=1, full=True)

        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["total"] == 0
        assert result["batch_errors"] == 0

    def test_empty_erp_response_incremental(self, db, default_tenant):
        existing = CosiumInvoice(
            tenant_id=default_tenant.id,
            cosium_id=500,
            invoice_number="EXIST-001",
            invoice_date=datetime(2026, 3, 1, tzinfo=UTC),
            customer_name="Client",
            type="INVOICE",
            total_ti=0.0,
            outstanding_balance=0.0,
            settled=True,
            archived=False,
        )
        db.add(existing)
        db.commit()

        connector = _mock_connector(invoices=[])

        with (
            patch(_AUTH_GET, return_value=(connector, default_tenant)),
            patch(_AUTH_AUTH),
            patch(_INV_AUDIT),
        ):
            from app.services.erp_sync_invoices import sync_invoices

            result = sync_invoices(db, tenant_id=default_tenant.id, user_id=1, full=False)

        assert result["created"] == 0
        assert result["total"] == 0

    def test_invoice_with_non_numeric_erp_id_skipped(self, db, default_tenant):
        bad_invoice = ERPInvoice(
            erp_id="N/A",  # non-digit -> skipped
            number="BAD-001",
            total_ttc=0.0,
        )
        connector = _mock_connector(invoices=[bad_invoice])

        with (
            patch(_AUTH_GET, return_value=(connector, default_tenant)),
            patch(_AUTH_AUTH),
            patch(_INV_AUDIT),
        ):
            from app.services.erp_sync_invoices import sync_invoices

            result = sync_invoices(db, tenant_id=default_tenant.id, user_id=1, full=True)

        assert result["created"] == 0
        assert result["total"] == 1  # fetched but skipped in upsert


class TestSyncInvoicesBatchErrors:
    """Batch flush errors are counted but do not abort the sync."""

    def test_batch_error_counted_sync_continues(self, db, default_tenant):
        from app.services.erp_sync_invoices import BATCH_SIZE

        invoices = [
            _make_erp_invoice(erp_id=str(1000 + i), number=f"F{i:04d}", customer_erp_id=f"C{i:04d}")
            for i in range(BATCH_SIZE)
        ]
        connector = _mock_connector(invoices=invoices)

        original_flush = db.flush
        call_count = {"n": 0}

        def patched_flush(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise SQLAlchemyError("simulated batch flush failure")
            return original_flush(*args, **kwargs)

        db.flush = patched_flush

        with (
            patch(_AUTH_GET, return_value=(connector, default_tenant)),
            patch(_AUTH_AUTH),
            patch(_INV_AUDIT),
        ):
            from app.services.erp_sync_invoices import sync_invoices

            result = sync_invoices(db, tenant_id=default_tenant.id, user_id=1, full=True)

        assert result["batch_errors"] == 1
        # The sync must complete without re-raising
        assert "created" in result

    def test_commit_failure_raises(self, db, default_tenant):
        connector = _mock_connector(invoices=[_make_erp_invoice()])

        with (
            patch(_AUTH_GET, return_value=(connector, default_tenant)),
            patch(_AUTH_AUTH),
            patch(_INV_AUDIT),
            patch.object(db, "commit", side_effect=SQLAlchemyError("commit boom")),
        ):
            from app.services.erp_sync_invoices import sync_invoices

            with pytest.raises(SQLAlchemyError):
                sync_invoices(db, tenant_id=default_tenant.id, user_id=1, full=True)

    def test_connection_error_during_fetch_raises_value_error(self, db, default_tenant):
        connector = _mock_connector()
        connector.get_invoices.side_effect = ConnectionError("ERP unreachable")

        with (
            patch(_AUTH_GET, return_value=(connector, default_tenant)),
            patch(_AUTH_AUTH),
            patch(_INV_AUDIT),
        ):
            from app.services.erp_sync_invoices import sync_invoices

            with pytest.raises(ValueError, match="Erreur critique"):
                sync_invoices(db, tenant_id=default_tenant.id, user_id=1, full=True)


class TestSyncInvoicesAudit:
    """Audit log is only created when user_id > 0."""

    def test_audit_log_called_with_user(self, db, default_tenant):
        connector = _mock_connector(invoices=[])

        with (
            patch(_AUTH_GET, return_value=(connector, default_tenant)),
            patch(_AUTH_AUTH),
            patch(_INV_AUDIT) as mock_audit,
        ):
            from app.services.erp_sync_invoices import sync_invoices

            sync_invoices(db, tenant_id=default_tenant.id, user_id=7, full=True)

        mock_audit.assert_called_once()
        assert mock_audit.call_args.args[2] == 7  # user_id

    def test_no_audit_log_without_user(self, db, default_tenant):
        connector = _mock_connector(invoices=[])

        with (
            patch(_AUTH_GET, return_value=(connector, default_tenant)),
            patch(_AUTH_AUTH),
            patch(_INV_AUDIT) as mock_audit,
        ):
            from app.services.erp_sync_invoices import sync_invoices

            sync_invoices(db, tenant_id=default_tenant.id, user_id=0, full=True)

        mock_audit.assert_not_called()

    def test_auth_failure_propagates(self, db, default_tenant):
        connector = _mock_connector(invoices=[])

        with (
            patch(_AUTH_GET, return_value=(connector, default_tenant)),
            patch(_AUTH_AUTH, side_effect=ValueError("Credentials non configurees")),
        ):
            from app.services.erp_sync_invoices import sync_invoices

            with pytest.raises(ValueError, match="Credentials"):
                sync_invoices(db, tenant_id=default_tenant.id, user_id=1, full=True)


# ===========================================================================
# PAYMENTS
# ===========================================================================


class TestSyncPaymentsHappyPath:
    """sync_payments creates and updates CosiumPayment rows correctly."""

    def _patch_payments(self, connector, default_tenant):
        """Return a context manager that patches all external deps for payments."""
        from contextlib import ExitStack

        stack = ExitStack()
        stack.enter_context(patch(_PAY_GET, return_value=(connector, default_tenant)))
        stack.enter_context(patch(_PAY_AUTH))
        # Make isinstance(connector, CosiumConnector) return True
        stack.enter_context(
            patch(
                "app.services.erp_sync_payments.CosiumConnector",
                new=type(connector),
            )
        )
        return stack

    def test_creates_new_payment(self, db, default_tenant):
        payment = _make_payment()
        connector = _mock_connector(payments=[payment])

        with (
            patch(_PAY_GET, return_value=(connector, default_tenant)),
            patch(_PAY_AUTH),
            patch(
                "app.services.erp_sync_payments.isinstance",
                return_value=True,
                create=True,
            ),
        ):
            # Patch CosiumConnector so isinstance check passes
            import app.integrations.cosium.cosium_connector as cc_mod

            with patch.object(cc_mod, "CosiumConnector", type(connector)):
                from app.services.erp_sync_payments import sync_payments

                result = sync_payments(db, tenant_id=default_tenant.id, user_id=1)

        assert result["created"] == 1
        assert result["updated"] == 0
        assert result["total"] == 1

        row = db.query(CosiumPayment).filter(CosiumPayment.tenant_id == default_tenant.id).first()
        assert row is not None
        assert row.cosium_id == 5001
        assert row.amount == 300.0
        assert row.type == "CB"

    def test_updates_existing_payment(self, db, default_tenant):
        existing = CosiumPayment(
            tenant_id=default_tenant.id,
            cosium_id=5001,
            amount=200.0,
            type="CHEQUE",
            issuer_name="DUPONT Jean",
            bank="BNP",
            site_name="Paris",
            payment_number="OLD-PMT",
        )
        db.add(existing)
        db.commit()

        payment = _make_payment(amount=300.0, type="CB")
        connector = _mock_connector(payments=[payment])

        import app.integrations.cosium.cosium_connector as cc_mod

        with (
            patch(_PAY_GET, return_value=(connector, default_tenant)),
            patch(_PAY_AUTH),
            patch.object(cc_mod, "CosiumConnector", type(connector)),
        ):
            from app.services.erp_sync_payments import sync_payments

            result = sync_payments(db, tenant_id=default_tenant.id, user_id=1)

        assert result["created"] == 0
        assert result["updated"] == 1
        db.refresh(existing)
        assert existing.amount == 300.0
        assert existing.type == "CB"

    def test_multiple_payments_created(self, db, default_tenant):
        payments = [_make_payment(cosium_id=5000 + i, invoice_cosium_id=1000 + i) for i in range(1, 4)]
        connector = _mock_connector(payments=payments)

        import app.integrations.cosium.cosium_connector as cc_mod

        with (
            patch(_PAY_GET, return_value=(connector, default_tenant)),
            patch(_PAY_AUTH),
            patch.object(cc_mod, "CosiumConnector", type(connector)),
        ):
            from app.services.erp_sync_payments import sync_payments

            result = sync_payments(db, tenant_id=default_tenant.id, user_id=1)

        assert result["created"] == 3
        assert result["total"] == 3


class TestSyncPaymentsIncrementalMode:
    """sync_payments uses max_pages for incremental fetch when records exist."""

    def _run_payments_sync(self, db, default_tenant, connector, *, full: bool = False):
        import app.integrations.cosium.cosium_connector as cc_mod

        with (
            patch(_PAY_GET, return_value=(connector, default_tenant)),
            patch(_PAY_AUTH),
            patch.object(cc_mod, "CosiumConnector", type(connector)),
        ):
            from app.services.erp_sync_payments import sync_payments

            return sync_payments(db, tenant_id=default_tenant.id, user_id=1, full=full)

    def test_incremental_calls_max_pages(self, db, default_tenant):
        # Pre-seed one payment so existing_count > 0
        existing = CosiumPayment(
            tenant_id=default_tenant.id,
            cosium_id=4000,
            amount=10.0,
            type="CB",
            issuer_name="Client",
            bank="",
            site_name="",
            payment_number="",
        )
        db.add(existing)
        db.commit()

        connector = _mock_connector(payments=[])
        self._run_payments_sync(db, default_tenant, connector, full=False)

        connector.get_invoice_payments.assert_called_once_with(max_pages=20)

    def test_full_sync_calls_without_max_pages(self, db, default_tenant):
        connector = _mock_connector(payments=[])
        self._run_payments_sync(db, default_tenant, connector, full=True)

        connector.get_invoice_payments.assert_called_once_with()

    def test_first_sync_no_existing_calls_full(self, db, default_tenant):
        """When no payments exist yet (regardless of full flag), calls without max_pages."""
        connector = _mock_connector(payments=[])
        self._run_payments_sync(db, default_tenant, connector, full=False)

        connector.get_invoice_payments.assert_called_once_with()


class TestSyncPaymentsEmptyERP:
    """sync_payments handles empty ERP response."""

    def test_empty_returns_zeros(self, db, default_tenant):
        connector = _mock_connector(payments=[])

        import app.integrations.cosium.cosium_connector as cc_mod

        with (
            patch(_PAY_GET, return_value=(connector, default_tenant)),
            patch(_PAY_AUTH),
            patch.object(cc_mod, "CosiumConnector", type(connector)),
        ):
            from app.services.erp_sync_payments import sync_payments

            result = sync_payments(db, tenant_id=default_tenant.id, user_id=1)

        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["total"] == 0

    def test_payment_without_cosium_id_skipped(self, db, default_tenant):
        bad_payment = {"cosium_id": None, "amount": 100.0, "type": "CB"}
        connector = _mock_connector(payments=[bad_payment])

        import app.integrations.cosium.cosium_connector as cc_mod

        with (
            patch(_PAY_GET, return_value=(connector, default_tenant)),
            patch(_PAY_AUTH),
            patch.object(cc_mod, "CosiumConnector", type(connector)),
        ):
            from app.services.erp_sync_payments import sync_payments

            result = sync_payments(db, tenant_id=default_tenant.id, user_id=1)

        assert result["created"] == 0
        assert result["total"] == 1  # fetched, but skipped

    def test_non_cosium_connector_returns_early(self, db, default_tenant):
        """When connector is not CosiumConnector, returns early note dict."""
        connector = MagicMock()
        connector.erp_type = "other"

        with (
            patch(_PAY_GET, return_value=(connector, default_tenant)),
            patch(_PAY_AUTH),
            # Leave CosiumConnector as-is so isinstance returns False
        ):
            from app.services.erp_sync_payments import sync_payments

            result = sync_payments(db, tenant_id=default_tenant.id, user_id=1)

        assert result["created"] == 0
        assert result["updated"] == 0
        assert "note" in result


class TestSyncPaymentsBatchErrors:
    """Batch flush errors increment batch_errors without aborting."""

    def test_batch_error_counted(self, db, default_tenant):
        from app.services._erp_sync_helpers import BATCH_SIZE

        payments = [_make_payment(cosium_id=6000 + i, invoice_cosium_id=2000 + i) for i in range(BATCH_SIZE)]
        connector = _mock_connector(payments=payments)

        original_flush = db.flush
        call_count = {"n": 0}

        def patched_flush(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise SQLAlchemyError("simulated flush fail")
            return original_flush(*args, **kwargs)

        db.flush = patched_flush

        import app.integrations.cosium.cosium_connector as cc_mod

        with (
            patch(_PAY_GET, return_value=(connector, default_tenant)),
            patch(_PAY_AUTH),
            patch.object(cc_mod, "CosiumConnector", type(connector)),
        ):
            from app.services.erp_sync_payments import sync_payments

            result = sync_payments(db, tenant_id=default_tenant.id, user_id=1)

        assert result["batch_errors"] == 1


class TestSyncPaymentsAudit:
    """sync_payments audit log behavior."""

    def _run(self, db, default_tenant, connector, user_id):
        import app.integrations.cosium.cosium_connector as cc_mod

        with (
            patch(_PAY_GET, return_value=(connector, default_tenant)),
            patch(_PAY_AUTH),
            patch.object(cc_mod, "CosiumConnector", type(connector)),
        ):
            from app.services.erp_sync_payments import sync_payments

            return sync_payments(db, tenant_id=default_tenant.id, user_id=user_id)

    def test_audit_called_with_user(self, db, default_tenant):
        connector = _mock_connector(payments=[])

        with patch("app.services._erp_sync_helpers.audit_service.log_action") as mock_audit:
            self._run(db, default_tenant, connector, user_id=5)

        mock_audit.assert_called_once()

    def test_no_audit_without_user(self, db, default_tenant):
        connector = _mock_connector(payments=[])

        with patch("app.services._erp_sync_helpers.audit_service.log_action") as mock_audit:
            self._run(db, default_tenant, connector, user_id=0)

        mock_audit.assert_not_called()


# ===========================================================================
# PRESCRIPTIONS
# ===========================================================================


class TestSyncPrescriptionsHappyPath:
    """sync_prescriptions creates and updates CosiumPrescription rows correctly."""

    def _run_prescriptions(self, db, default_tenant, connector, *, full: bool = False):
        import app.integrations.cosium.cosium_connector as cc_mod

        with (
            patch(_PRESC_GET, return_value=(connector, default_tenant)),
            patch(_PRESC_AUTH),
            patch.object(cc_mod, "CosiumConnector", type(connector)),
        ):
            from app.services.erp_sync_prescriptions import sync_prescriptions

            return sync_prescriptions(db, tenant_id=default_tenant.id, user_id=1, full=full)

    def test_creates_new_prescription(self, db, default_tenant):
        presc = _make_prescription()
        connector = _mock_connector(prescriptions=[presc])

        result = self._run_prescriptions(db, default_tenant, connector, full=True)

        assert result["created"] == 1
        assert result["updated"] == 0
        assert result["total"] == 1

        row = db.query(CosiumPrescription).filter(
            CosiumPrescription.tenant_id == default_tenant.id
        ).first()
        assert row is not None
        assert row.cosium_id == 7001
        assert row.sphere_right == -1.5
        assert row.sphere_left == -1.25
        assert row.prescriber_name == "Dr. Moreau"

    def test_updates_existing_prescription(self, db, default_tenant):
        existing = CosiumPrescription(
            tenant_id=default_tenant.id,
            cosium_id=7001,
            sphere_right=-1.0,
            sphere_left=-1.0,
            prescription_date="2025-10-01",
            prescriber_name="Dr. Ancien",
        )
        db.add(existing)
        db.commit()

        presc = _make_prescription(sphere_right=-2.0, sphere_left=-1.75)
        connector = _mock_connector(prescriptions=[presc])

        result = self._run_prescriptions(db, default_tenant, connector, full=True)

        assert result["created"] == 0
        assert result["updated"] == 1
        db.refresh(existing)
        assert existing.sphere_right == -2.0
        assert existing.sphere_left == -1.75
        assert existing.prescriber_name == "Dr. Moreau"

    def test_multiple_prescriptions_all_created(self, db, default_tenant):
        prescriptions = [_make_prescription(cosium_id=7000 + i, customer_cosium_id=100 + i) for i in range(1, 5)]
        connector = _mock_connector(prescriptions=prescriptions)

        result = self._run_prescriptions(db, default_tenant, connector, full=True)

        assert result["created"] == 4
        assert result["total"] == 4

    def test_prescription_file_date_parsed(self, db, default_tenant):
        presc = _make_prescription(file_date="2025-11-05T10:00:00.000Z")
        connector = _mock_connector(prescriptions=[presc])

        self._run_prescriptions(db, default_tenant, connector, full=True)

        row = db.query(CosiumPrescription).filter(CosiumPrescription.cosium_id == 7001).first()
        assert row is not None
        assert row.file_date is not None


class TestSyncPrescriptionsIncrementalMode:
    """sync_prescriptions uses max_pages when records exist."""

    def _run(self, db, default_tenant, connector, *, full: bool = False):
        import app.integrations.cosium.cosium_connector as cc_mod

        with (
            patch(_PRESC_GET, return_value=(connector, default_tenant)),
            patch(_PRESC_AUTH),
            patch.object(cc_mod, "CosiumConnector", type(connector)),
        ):
            from app.services.erp_sync_prescriptions import sync_prescriptions

            return sync_prescriptions(db, tenant_id=default_tenant.id, user_id=1, full=full)

    def test_incremental_calls_max_pages(self, db, default_tenant):
        # Pre-seed a prescription so existing_count > 0
        existing = CosiumPrescription(
            tenant_id=default_tenant.id,
            cosium_id=6001,
            prescription_date="2025-01-01",
        )
        db.add(existing)
        db.commit()

        connector = _mock_connector(prescriptions=[])
        self._run(db, default_tenant, connector, full=False)

        connector.get_optical_prescriptions.assert_called_once_with(max_pages=20)

    def test_full_sync_no_max_pages(self, db, default_tenant):
        connector = _mock_connector(prescriptions=[])
        self._run(db, default_tenant, connector, full=True)

        connector.get_optical_prescriptions.assert_called_once_with()

    def test_first_sync_no_existing_calls_full(self, db, default_tenant):
        connector = _mock_connector(prescriptions=[])
        self._run(db, default_tenant, connector, full=False)

        connector.get_optical_prescriptions.assert_called_once_with()


class TestSyncPrescriptionsEmptyERP:
    """sync_prescriptions handles empty ERP responses."""

    def _run(self, db, default_tenant, connector, *, full: bool = True):
        import app.integrations.cosium.cosium_connector as cc_mod

        with (
            patch(_PRESC_GET, return_value=(connector, default_tenant)),
            patch(_PRESC_AUTH),
            patch.object(cc_mod, "CosiumConnector", type(connector)),
        ):
            from app.services.erp_sync_prescriptions import sync_prescriptions

            return sync_prescriptions(db, tenant_id=default_tenant.id, user_id=1, full=full)

    def test_empty_response_returns_zeros(self, db, default_tenant):
        connector = _mock_connector(prescriptions=[])
        result = self._run(db, default_tenant, connector)

        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["total"] == 0
        assert result["batch_errors"] == 0

    def test_prescription_without_cosium_id_skipped(self, db, default_tenant):
        bad = {"cosium_id": None, "sphere_right": -1.0}
        connector = _mock_connector(prescriptions=[bad])
        result = self._run(db, default_tenant, connector)

        assert result["created"] == 0
        assert result["total"] == 1  # fetched, skipped in loop

    def test_non_cosium_connector_returns_early(self, db, default_tenant):
        """Non-CosiumConnector returns early note dict."""
        connector = MagicMock()
        connector.erp_type = "other"

        with (
            patch(_PRESC_GET, return_value=(connector, default_tenant)),
            patch(_PRESC_AUTH),
        ):
            from app.services.erp_sync_prescriptions import sync_prescriptions

            result = sync_prescriptions(db, tenant_id=default_tenant.id, user_id=1)

        assert result["created"] == 0
        assert "note" in result


class TestSyncPrescriptionsBatchErrors:
    """Batch flush errors are counted but sync continues."""

    def test_batch_error_counted(self, db, default_tenant):
        from app.services._erp_sync_helpers import BATCH_SIZE

        prescriptions = [
            _make_prescription(cosium_id=8000 + i, customer_cosium_id=200 + i)
            for i in range(BATCH_SIZE)
        ]
        connector = _mock_connector(prescriptions=prescriptions)

        original_flush = db.flush
        call_count = {"n": 0}

        def patched_flush(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise SQLAlchemyError("simulated flush fail")
            return original_flush(*args, **kwargs)

        db.flush = patched_flush

        import app.integrations.cosium.cosium_connector as cc_mod

        with (
            patch(_PRESC_GET, return_value=(connector, default_tenant)),
            patch(_PRESC_AUTH),
            patch.object(cc_mod, "CosiumConnector", type(connector)),
        ):
            from app.services.erp_sync_prescriptions import sync_prescriptions

            result = sync_prescriptions(db, tenant_id=default_tenant.id, user_id=1, full=True)

        assert result["batch_errors"] == 1

    def test_commit_failure_raises(self, db, default_tenant):
        presc = _make_prescription()
        connector = _mock_connector(prescriptions=[presc])

        import app.integrations.cosium.cosium_connector as cc_mod

        with (
            patch(_PRESC_GET, return_value=(connector, default_tenant)),
            patch(_PRESC_AUTH),
            patch.object(cc_mod, "CosiumConnector", type(connector)),
            patch.object(db, "commit", side_effect=SQLAlchemyError("commit fail")),
        ):
            from app.services.erp_sync_prescriptions import sync_prescriptions

            with pytest.raises(SQLAlchemyError):
                sync_prescriptions(db, tenant_id=default_tenant.id, user_id=1, full=True)


class TestSyncPrescriptionsAudit:
    """sync_prescriptions audit log behavior."""

    def _run(self, db, default_tenant, connector, user_id: int):
        import app.integrations.cosium.cosium_connector as cc_mod

        with (
            patch(_PRESC_GET, return_value=(connector, default_tenant)),
            patch(_PRESC_AUTH),
            patch.object(cc_mod, "CosiumConnector", type(connector)),
        ):
            from app.services.erp_sync_prescriptions import sync_prescriptions

            return sync_prescriptions(db, tenant_id=default_tenant.id, user_id=user_id, full=True)

    def test_audit_called_with_user(self, db, default_tenant):
        connector = _mock_connector(prescriptions=[])

        with patch("app.services._erp_sync_helpers.audit_service.log_action") as mock_audit:
            self._run(db, default_tenant, connector, user_id=9)

        mock_audit.assert_called_once()

    def test_no_audit_without_user(self, db, default_tenant):
        connector = _mock_connector(prescriptions=[])

        with patch("app.services._erp_sync_helpers.audit_service.log_action") as mock_audit:
            self._run(db, default_tenant, connector, user_id=0)

        mock_audit.assert_not_called()

    def test_auth_failure_propagates(self, db, default_tenant):
        connector = _mock_connector(prescriptions=[])

        with (
            patch(_PRESC_GET, return_value=(connector, default_tenant)),
            patch(_PRESC_AUTH, side_effect=ValueError("Credentials manquantes")),
        ):
            from app.services.erp_sync_prescriptions import sync_prescriptions

            with pytest.raises(ValueError, match="Credentials"):
                sync_prescriptions(db, tenant_id=default_tenant.id, user_id=1, full=True)
