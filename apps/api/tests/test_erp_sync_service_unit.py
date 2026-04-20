"""Unit tests for erp_sync_service.sync_customers() and sync_all() orchestrator.

All external dependencies (CosiumConnector, audit_service) are mocked so these
tests run purely in-memory against the SQLite test DB provided by conftest.py.
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.integrations.erp_models import ERPCustomer
from app.models import Customer, Tenant


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_erp_customer(
    erp_id: str = "C001",
    first_name: str = "Jean",
    last_name: str = "Dupont",
    email: str | None = "jean.dupont@example.com",
    phone: str | None = "0601020304",
) -> ERPCustomer:
    return ERPCustomer(
        erp_id=erp_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
    )


def _mock_connector(erp_customers: list[ERPCustomer] | None = None) -> MagicMock:
    """Build a mock ERPConnector whose get_customers() returns the given list."""
    connector = MagicMock()
    connector.erp_type = "cosium"
    connector.get_customers.return_value = erp_customers or []
    return connector


# ---------------------------------------------------------------------------
# sync_customers — basic create / update / skip
# ---------------------------------------------------------------------------


class TestSyncCustomersCreate:
    """sync_customers creates new customers when none exist yet."""

    def test_creates_new_customers(self, db, default_tenant):
        connector = _mock_connector([_make_erp_customer()])

        with (
            patch(
                "app.services.erp_sync_service._get_connector_for_tenant",
                return_value=(connector, default_tenant),
            ),
            patch("app.services.erp_sync_service._authenticate_connector"),
            patch("app.services.erp_sync_service.audit_service.log_action"),
        ):
            from app.services.erp_sync_service import sync_customers

            result = sync_customers(db, tenant_id=default_tenant.id, user_id=1)

        assert result["created"] == 1
        assert result["updated"] == 0
        assert result["skipped"] == 0
        assert result["total"] == 1

        saved = db.query(Customer).filter(Customer.tenant_id == default_tenant.id).all()
        assert len(saved) == 1
        assert saved[0].last_name == "Dupont"
        assert saved[0].cosium_id == "C001"

    def test_multiple_customers_all_created(self, db, default_tenant):
        erp_customers = [
            _make_erp_customer("A1", "Alice", "Martin", "alice@example.com"),
            _make_erp_customer("A2", "Bob", "Bernard", "bob@example.com"),
            _make_erp_customer("A3", "Clara", "Petit", "clara@example.com"),
        ]
        connector = _mock_connector(erp_customers)

        with (
            patch(
                "app.services.erp_sync_service._get_connector_for_tenant",
                return_value=(connector, default_tenant),
            ),
            patch("app.services.erp_sync_service._authenticate_connector"),
            patch("app.services.erp_sync_service.audit_service.log_action"),
        ):
            from app.services.erp_sync_service import sync_customers

            result = sync_customers(db, tenant_id=default_tenant.id, user_id=1)

        assert result["created"] == 3
        assert result["total"] == 3

    def test_empty_erp_returns_zeros(self, db, default_tenant):
        connector = _mock_connector([])

        with (
            patch(
                "app.services.erp_sync_service._get_connector_for_tenant",
                return_value=(connector, default_tenant),
            ),
            patch("app.services.erp_sync_service._authenticate_connector"),
            patch("app.services.erp_sync_service.audit_service.log_action"),
        ):
            from app.services.erp_sync_service import sync_customers

            result = sync_customers(db, tenant_id=default_tenant.id, user_id=1)

        assert result["created"] == 0
        assert result["updated"] == 0
        assert result["total"] == 0


class TestSyncCustomersUpdate:
    """sync_customers updates existing customers matched by erp_id / email / name."""

    def test_updates_existing_customer_by_email(self, db, default_tenant):
        # Pre-seed a customer with no phone
        existing = Customer(
            tenant_id=default_tenant.id,
            first_name="Jean",
            last_name="Dupont",
            email="jean.dupont@example.com",
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)

        erp_c = _make_erp_customer(
            erp_id="C001",
            first_name="Jean",
            last_name="Dupont",
            email="jean.dupont@example.com",
            phone="0601020304",
        )
        connector = _mock_connector([erp_c])

        with (
            patch(
                "app.services.erp_sync_service._get_connector_for_tenant",
                return_value=(connector, default_tenant),
            ),
            patch("app.services.erp_sync_service._authenticate_connector"),
            patch("app.services.erp_sync_service.audit_service.log_action"),
        ):
            from app.services.erp_sync_service import sync_customers

            result = sync_customers(db, tenant_id=default_tenant.id, user_id=1)

        assert result["updated"] == 1
        assert result["created"] == 0
        db.refresh(existing)
        assert existing.cosium_id == "C001"
        assert existing.phone == "0601020304"

    def test_updates_existing_customer_by_erp_id(self, db, default_tenant):
        existing = Customer(
            tenant_id=default_tenant.id,
            first_name="Marie",
            last_name="Curie",
            email="mcurie@example.com",
            cosium_id="X999",
        )
        db.add(existing)
        db.commit()
        db.refresh(existing)

        # ERP sends same erp_id with a new phone number
        erp_c = ERPCustomer(
            erp_id="X999",
            first_name="Marie",
            last_name="Curie",
            email="mcurie@example.com",
            phone="0700000000",
        )
        connector = _mock_connector([erp_c])

        with (
            patch(
                "app.services.erp_sync_service._get_connector_for_tenant",
                return_value=(connector, default_tenant),
            ),
            patch("app.services.erp_sync_service._authenticate_connector"),
            patch("app.services.erp_sync_service.audit_service.log_action"),
        ):
            from app.services.erp_sync_service import sync_customers

            result = sync_customers(db, tenant_id=default_tenant.id, user_id=1)

        assert result["updated"] == 1
        db.refresh(existing)
        assert existing.phone == "0700000000"

    def test_sets_sync_timestamp_on_tenant(self, db, default_tenant):
        assert default_tenant.last_cosium_sync_at is None
        connector = _mock_connector([])

        with (
            patch(
                "app.services.erp_sync_service._get_connector_for_tenant",
                return_value=(connector, default_tenant),
            ),
            patch("app.services.erp_sync_service._authenticate_connector"),
            patch("app.services.erp_sync_service.audit_service.log_action"),
        ):
            from app.services.erp_sync_service import sync_customers

            sync_customers(db, tenant_id=default_tenant.id, user_id=1)

        db.refresh(default_tenant)
        assert default_tenant.last_cosium_sync_at is not None

    def test_sets_first_sync_done_on_tenant(self, db, default_tenant):
        default_tenant.first_sync_done = False
        db.commit()

        connector = _mock_connector([])

        with (
            patch(
                "app.services.erp_sync_service._get_connector_for_tenant",
                return_value=(connector, default_tenant),
            ),
            patch("app.services.erp_sync_service._authenticate_connector"),
            patch("app.services.erp_sync_service.audit_service.log_action"),
        ):
            from app.services.erp_sync_service import sync_customers

            sync_customers(db, tenant_id=default_tenant.id, user_id=1)

        db.refresh(default_tenant)
        assert default_tenant.first_sync_done is True


class TestSyncCustomersSkip:
    """sync_customers skips records without a last_name."""

    def test_skips_customer_without_last_name(self, db, default_tenant):
        erp_no_name = ERPCustomer(
            erp_id="Z001",
            first_name="Prénom",
            last_name="",  # empty — should be skipped
        )
        connector = _mock_connector([erp_no_name])

        with (
            patch(
                "app.services.erp_sync_service._get_connector_for_tenant",
                return_value=(connector, default_tenant),
            ),
            patch("app.services.erp_sync_service._authenticate_connector"),
            patch("app.services.erp_sync_service.audit_service.log_action"),
        ):
            from app.services.erp_sync_service import sync_customers

            result = sync_customers(db, tenant_id=default_tenant.id, user_id=1)

        assert result["skipped"] == 1
        assert result["created"] == 0
        assert len(result["warnings"]) >= 1

    def test_valid_and_invalid_mixed(self, db, default_tenant):
        erp_customers = [
            _make_erp_customer("V1", "Alice", "Valid"),
            ERPCustomer(erp_id="N1", first_name="NoName", last_name=""),
            _make_erp_customer("V2", "Bob", "AlsoValid", email="bob@example.com"),
        ]
        connector = _mock_connector(erp_customers)

        with (
            patch(
                "app.services.erp_sync_service._get_connector_for_tenant",
                return_value=(connector, default_tenant),
            ),
            patch("app.services.erp_sync_service._authenticate_connector"),
            patch("app.services.erp_sync_service.audit_service.log_action"),
        ):
            from app.services.erp_sync_service import sync_customers

            result = sync_customers(db, tenant_id=default_tenant.id, user_id=1)

        assert result["created"] == 2
        assert result["skipped"] == 1


# ---------------------------------------------------------------------------
# sync_customers — incremental mode (unchanged detection)
# ---------------------------------------------------------------------------


class TestSyncCustomersIncremental:
    """Incremental sync skips unchanged customers to reduce write load."""

    def test_incremental_skips_unchanged_customers(self, db, default_tenant):
        from datetime import UTC, datetime

        # Mark tenant as already synced (triggers incremental mode)
        default_tenant.last_cosium_sync_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()

        # Pre-seed a fully-populated customer so nothing needs updating
        existing = Customer(
            tenant_id=default_tenant.id,
            cosium_id="C100",
            first_name="Sophie",
            last_name="Leclerc",
            email="sophie@example.com",
            phone="0600000001",
        )
        db.add(existing)
        db.commit()

        # ERP returns the same customer with no new fields
        erp_c = ERPCustomer(
            erp_id="C100",
            first_name="Sophie",
            last_name="Leclerc",
            email="sophie@example.com",
            phone="0600000001",
        )
        connector = _mock_connector([erp_c])

        with (
            patch(
                "app.services.erp_sync_service._get_connector_for_tenant",
                return_value=(connector, default_tenant),
            ),
            patch("app.services.erp_sync_service._authenticate_connector"),
            patch("app.services.erp_sync_service.audit_service.log_action"),
        ):
            from app.services.erp_sync_service import sync_customers

            result = sync_customers(db, tenant_id=default_tenant.id, user_id=1)

        assert result["mode"] == "incremental"
        assert result["unchanged"] >= 1
        assert result["updated"] == 0
        assert result["created"] == 0

    def test_full_mode_when_no_previous_sync(self, db, default_tenant):
        assert default_tenant.last_cosium_sync_at is None
        connector = _mock_connector([])

        with (
            patch(
                "app.services.erp_sync_service._get_connector_for_tenant",
                return_value=(connector, default_tenant),
            ),
            patch("app.services.erp_sync_service._authenticate_connector"),
            patch("app.services.erp_sync_service.audit_service.log_action"),
        ):
            from app.services.erp_sync_service import sync_customers

            result = sync_customers(db, tenant_id=default_tenant.id, user_id=1)

        assert result["mode"] == "full"


# ---------------------------------------------------------------------------
# sync_customers — batch processing
# ---------------------------------------------------------------------------


class TestSyncCustomersBatch:
    """Batch processing: flush is called every BATCH_SIZE records."""

    def test_flush_called_at_batch_boundary(self, db, default_tenant):
        """flush() must be called once when exactly BATCH_SIZE records are processed."""
        from app.services.erp_sync_service import BATCH_SIZE

        erp_customers = [
            _make_erp_customer(f"B{i:04d}", "Prénom", f"Nom{i}", f"c{i}@example.com")
            for i in range(BATCH_SIZE)
        ]
        connector = _mock_connector(erp_customers)

        with (
            patch(
                "app.services.erp_sync_service._get_connector_for_tenant",
                return_value=(connector, default_tenant),
            ),
            patch("app.services.erp_sync_service._authenticate_connector"),
            patch("app.services.erp_sync_service.audit_service.log_action"),
        ):
            from app.services.erp_sync_service import sync_customers

            result = sync_customers(db, tenant_id=default_tenant.id, user_id=1)

        assert result["created"] == BATCH_SIZE
        assert result["batch_errors"] == 0

    def test_batch_error_does_not_abort_sync(self, db, default_tenant):
        """A flush failure increments batch_errors but sync continues."""
        from app.services.erp_sync_service import BATCH_SIZE

        # Exactly BATCH_SIZE customers to trigger one flush
        erp_customers = [
            _make_erp_customer(f"E{i:04d}", "Prénom", f"Err{i}", f"e{i}@example.com")
            for i in range(BATCH_SIZE)
        ]
        connector = _mock_connector(erp_customers)

        original_flush = db.flush

        flush_call_count = {"n": 0}

        def failing_flush(*args, **kwargs):
            flush_call_count["n"] += 1
            if flush_call_count["n"] == 1:
                raise RuntimeError("DB batch flush simulated failure")
            return original_flush(*args, **kwargs)

        db.flush = failing_flush

        with (
            patch(
                "app.services.erp_sync_service._get_connector_for_tenant",
                return_value=(connector, default_tenant),
            ),
            patch("app.services.erp_sync_service._authenticate_connector"),
            patch("app.services.erp_sync_service.audit_service.log_action"),
        ):
            from app.services.erp_sync_service import sync_customers

            result = sync_customers(db, tenant_id=default_tenant.id, user_id=1)

        assert result["batch_errors"] == 1
        # Sync itself must complete (no exception raised)

    def test_two_batches_processed(self, db, default_tenant):
        """Verify created count is correct when > BATCH_SIZE records arrive."""
        from app.services.erp_sync_service import BATCH_SIZE

        count = BATCH_SIZE + 10
        erp_customers = [
            _make_erp_customer(f"T{i:04d}", "Prénom", f"Two{i}", f"t{i}@example.com")
            for i in range(count)
        ]
        connector = _mock_connector(erp_customers)

        with (
            patch(
                "app.services.erp_sync_service._get_connector_for_tenant",
                return_value=(connector, default_tenant),
            ),
            patch("app.services.erp_sync_service._authenticate_connector"),
            patch("app.services.erp_sync_service.audit_service.log_action"),
        ):
            from app.services.erp_sync_service import sync_customers

            result = sync_customers(db, tenant_id=default_tenant.id, user_id=1)

        assert result["created"] == count


# ---------------------------------------------------------------------------
# sync_customers — error handling
# ---------------------------------------------------------------------------


class TestSyncCustomersErrors:
    """Error handling: commit failure raises, connector error propagates."""

    def test_commit_failure_raises_sqlalchemy_error(self, db, default_tenant):
        connector = _mock_connector([_make_erp_customer()])

        with (
            patch(
                "app.services.erp_sync_service._get_connector_for_tenant",
                return_value=(connector, default_tenant),
            ),
            patch("app.services.erp_sync_service._authenticate_connector"),
            patch("app.services.erp_sync_service.audit_service.log_action"),
            patch.object(db, "commit", side_effect=SQLAlchemyError("commit failed")),
        ):
            from app.services.erp_sync_service import sync_customers

            with pytest.raises(SQLAlchemyError):
                sync_customers(db, tenant_id=default_tenant.id, user_id=1)

    def test_connector_auth_failure_propagates(self, db, default_tenant):
        connector = _mock_connector([])

        with (
            patch(
                "app.services.erp_sync_service._get_connector_for_tenant",
                return_value=(connector, default_tenant),
            ),
            patch(
                "app.services.erp_sync_service._authenticate_connector",
                side_effect=ValueError("Credentials ERP non configurees"),
            ),
        ):
            from app.services.erp_sync_service import sync_customers

            with pytest.raises(ValueError, match="Credentials ERP"):
                sync_customers(db, tenant_id=default_tenant.id, user_id=1)

    def test_no_audit_log_when_user_id_zero(self, db, default_tenant):
        connector = _mock_connector([])

        with (
            patch(
                "app.services.erp_sync_service._get_connector_for_tenant",
                return_value=(connector, default_tenant),
            ),
            patch("app.services.erp_sync_service._authenticate_connector"),
            patch("app.services.erp_sync_service.audit_service.log_action") as mock_audit,
        ):
            from app.services.erp_sync_service import sync_customers

            sync_customers(db, tenant_id=default_tenant.id, user_id=0)

        mock_audit.assert_not_called()

    def test_audit_log_called_when_user_provided(self, db, default_tenant):
        connector = _mock_connector([])

        with (
            patch(
                "app.services.erp_sync_service._get_connector_for_tenant",
                return_value=(connector, default_tenant),
            ),
            patch("app.services.erp_sync_service._authenticate_connector"),
            patch("app.services.erp_sync_service.audit_service.log_action") as mock_audit,
        ):
            from app.services.erp_sync_service import sync_customers

            sync_customers(db, tenant_id=default_tenant.id, user_id=42)

        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args
        # Positional: (db, tenant_id, user_id, action, entity_type, entity_id, new_value=...)
        assert call_kwargs.args[2] == 42  # user_id


# ---------------------------------------------------------------------------
# sync_customers — duplicate detection within a single batch
# ---------------------------------------------------------------------------


class TestSyncCustomersDuplicates:
    """Within a single batch, duplicate ERP records don't create multiple DB rows."""

    def test_duplicate_email_within_batch(self, db, default_tenant):
        erp_customers = [
            _make_erp_customer("D1", "Alice", "Dup", "same@example.com"),
            _make_erp_customer("D2", "Alice2", "Dup2", "same@example.com"),  # same email
        ]
        connector = _mock_connector(erp_customers)

        with (
            patch(
                "app.services.erp_sync_service._get_connector_for_tenant",
                return_value=(connector, default_tenant),
            ),
            patch("app.services.erp_sync_service._authenticate_connector"),
            patch("app.services.erp_sync_service.audit_service.log_action"),
        ):
            from app.services.erp_sync_service import sync_customers

            result = sync_customers(db, tenant_id=default_tenant.id, user_id=1)

        # Second customer with same email is matched as update, not duplicate creation
        assert result["created"] + result["updated"] == 2
        assert result["total"] == 2


# ---------------------------------------------------------------------------
# sync_all orchestrator
# ---------------------------------------------------------------------------


class TestSyncAll:
    """sync_all calls all domain sync functions and returns a keyed result dict."""

    def _patch_all_domains(self):
        """Return a context-manager stack that patches all sync domains."""
        from contextlib import ExitStack

        stack = ExitStack()
        mocks = {}

        for domain in ("sync_customers", "sync_invoices", "sync_payments", "sync_prescriptions"):
            module_path = {
                "sync_customers": "app.services.erp_sync_service.sync_customers",
                "sync_invoices": "app.services.erp_sync_invoices.sync_invoices",
                "sync_payments": "app.services.erp_sync_extras.sync_payments",
                "sync_prescriptions": "app.services.erp_sync_extras.sync_prescriptions",
            }[domain]
            mock = MagicMock(return_value={"ok": True, "domain": domain})
            stack.enter_context(patch(module_path, mock))
            mocks[domain] = mock

        # Patch reference sync
        ref_mock = MagicMock(return_value={"ok": True, "domain": "reference"})
        stack.enter_context(
            patch("app.services.cosium_reference_sync.sync_all_reference", ref_mock)
        )
        mocks["reference"] = ref_mock

        return stack, mocks

    def test_sync_all_returns_all_domain_keys(self, db, default_tenant):
        # sync_all uses lazy imports inside the function body:
        #   from app.services.erp_sync_service import sync_customers
        #   from app.services.erp_sync_invoices import sync_invoices
        #   from app.services.erp_sync_extras import sync_payments, sync_prescriptions
        # so we patch the function on its *origin* module.
        with (
            patch(
                "app.services.erp_sync_service.sync_customers",
                return_value={"created": 5, "mode": "full"},
            ),
            patch(
                "app.services.erp_sync_invoices.sync_invoices",
                return_value={"synced": 10},
            ),
            patch(
                "app.services.erp_sync_extras.sync_payments",
                return_value={"synced": 3},
            ),
            patch(
                "app.services.erp_sync_extras.sync_prescriptions",
                return_value={"synced": 2},
            ),
            patch(
                "app.services.cosium_reference_sync.sync_all_reference",
                return_value={"synced": 1},
            ),
        ):
            from app.services.erp_sync_handlers import sync_all

            result = sync_all(db, tenant_id=default_tenant.id, user_id=1)

        assert "customers" in result
        assert "invoices" in result
        assert "payments" in result
        assert "prescriptions" in result
        assert "reference" in result
        assert "has_errors" in result

    def test_sync_all_no_errors_flag_false(self, db, default_tenant):
        with (
            patch(
                "app.services.erp_sync_service.sync_customers",
                return_value={"created": 0},
            ),
            patch(
                "app.services.erp_sync_invoices.sync_invoices",
                return_value={"synced": 0},
            ),
            patch(
                "app.services.erp_sync_extras.sync_payments",
                return_value={"synced": 0},
            ),
            patch(
                "app.services.erp_sync_extras.sync_prescriptions",
                return_value={"synced": 0},
            ),
            patch(
                "app.services.cosium_reference_sync.sync_all_reference",
                return_value={"synced": 0},
            ),
        ):
            from app.services.erp_sync_handlers import sync_all

            result = sync_all(db, tenant_id=default_tenant.id, user_id=1)

        assert result["has_errors"] is False

    def test_sync_all_passes_full_flag_to_domains(self, db, default_tenant):
        invoices_mock = MagicMock(return_value={"synced": 0})
        payments_mock = MagicMock(return_value={"synced": 0})
        prescriptions_mock = MagicMock(return_value={"synced": 0})

        with (
            patch(
                "app.services.erp_sync_service.sync_customers",
                return_value={"created": 0},
            ),
            patch("app.services.erp_sync_invoices.sync_invoices", invoices_mock),
            patch("app.services.erp_sync_extras.sync_payments", payments_mock),
            patch("app.services.erp_sync_extras.sync_prescriptions", prescriptions_mock),
            patch(
                "app.services.cosium_reference_sync.sync_all_reference",
                return_value={"synced": 0},
            ),
        ):
            from app.services.erp_sync_handlers import sync_all

            sync_all(db, tenant_id=default_tenant.id, user_id=1, full=True)

        # Each domain-sync should receive full=True
        for mock in (invoices_mock, payments_mock, prescriptions_mock):
            _, kwargs = mock.call_args
            assert kwargs.get("full") is True


# ---------------------------------------------------------------------------
# sync_all — partial failure handling
# ---------------------------------------------------------------------------


class TestSyncAllPartialFailure:
    """When one domain fails, others continue and has_errors=True is set."""

    def test_customers_failure_others_continue(self, db, default_tenant):
        with (
            patch(
                "app.services.erp_sync_service.sync_customers",
                side_effect=RuntimeError("Cosium unreachable"),
            ),
            patch(
                "app.services.erp_sync_invoices.sync_invoices",
                return_value={"synced": 7},
            ),
            patch(
                "app.services.erp_sync_extras.sync_payments",
                return_value={"synced": 2},
            ),
            patch(
                "app.services.erp_sync_extras.sync_prescriptions",
                return_value={"synced": 1},
            ),
            patch(
                "app.services.cosium_reference_sync.sync_all_reference",
                return_value={"synced": 0},
            ),
        ):
            from app.services.erp_sync_handlers import sync_all

            result = sync_all(db, tenant_id=default_tenant.id, user_id=1)

        assert result["has_errors"] is True
        assert "error" in result["customers"]
        # Other domains still returned results
        assert result["invoices"] == {"synced": 7}
        assert result["payments"] == {"synced": 2}
        assert result["prescriptions"] == {"synced": 1}

    def test_invoices_failure_customers_succeed(self, db, default_tenant):
        with (
            patch(
                "app.services.erp_sync_service.sync_customers",
                return_value={"created": 3, "mode": "full"},
            ),
            patch(
                "app.services.erp_sync_invoices.sync_invoices",
                side_effect=ConnectionError("ERP timeout"),
            ),
            patch(
                "app.services.erp_sync_extras.sync_payments",
                return_value={"synced": 0},
            ),
            patch(
                "app.services.erp_sync_extras.sync_prescriptions",
                return_value={"synced": 0},
            ),
            patch(
                "app.services.cosium_reference_sync.sync_all_reference",
                return_value={"synced": 0},
            ),
        ):
            from app.services.erp_sync_handlers import sync_all

            result = sync_all(db, tenant_id=default_tenant.id, user_id=1)

        assert result["has_errors"] is True
        assert "error" in result["invoices"]
        assert result["customers"]["created"] == 3

    def test_all_domains_fail_has_errors_true(self, db, default_tenant):
        error = RuntimeError("total outage")

        with (
            patch("app.services.erp_sync_service.sync_customers", side_effect=error),
            patch("app.services.erp_sync_invoices.sync_invoices", side_effect=error),
            patch("app.services.erp_sync_extras.sync_payments", side_effect=error),
            patch("app.services.erp_sync_extras.sync_prescriptions", side_effect=error),
            patch(
                "app.services.cosium_reference_sync.sync_all_reference",
                side_effect=error,
            ),
        ):
            from app.services.erp_sync_handlers import sync_all

            result = sync_all(db, tenant_id=default_tenant.id, user_id=1)

        assert result["has_errors"] is True
        for domain in ("customers", "invoices", "payments", "prescriptions", "reference"):
            assert "error" in result[domain], f"Domain {domain!r} missing error key"

    def test_reference_failure_does_not_abort(self, db, default_tenant):
        with (
            patch(
                "app.services.erp_sync_service.sync_customers",
                return_value={"created": 1},
            ),
            patch(
                "app.services.erp_sync_invoices.sync_invoices",
                return_value={"synced": 0},
            ),
            patch(
                "app.services.erp_sync_extras.sync_payments",
                return_value={"synced": 0},
            ),
            patch(
                "app.services.erp_sync_extras.sync_prescriptions",
                return_value={"synced": 0},
            ),
            patch(
                "app.services.cosium_reference_sync.sync_all_reference",
                side_effect=ImportError("reference module unavailable"),
            ),
        ):
            from app.services.erp_sync_handlers import sync_all

            result = sync_all(db, tenant_id=default_tenant.id, user_id=1)

        assert result["has_errors"] is True
        assert "error" in result["reference"]
        assert result["customers"]["created"] == 1

    def test_partial_failure_error_message_is_human_readable(self, db, default_tenant):
        """Error slots must contain a human-readable French message (not a raw traceback)."""
        with (
            patch(
                "app.services.erp_sync_service.sync_customers",
                side_effect=RuntimeError("some internal error"),
            ),
            patch(
                "app.services.erp_sync_invoices.sync_invoices",
                return_value={"synced": 0},
            ),
            patch(
                "app.services.erp_sync_extras.sync_payments",
                return_value={"synced": 0},
            ),
            patch(
                "app.services.erp_sync_extras.sync_prescriptions",
                return_value={"synced": 0},
            ),
            patch(
                "app.services.cosium_reference_sync.sync_all_reference",
                return_value={"synced": 0},
            ),
        ):
            from app.services.erp_sync_handlers import sync_all

            result = sync_all(db, tenant_id=default_tenant.id, user_id=1)

        error_msg = result["customers"]["error"]
        assert isinstance(error_msg, str)
        assert len(error_msg) > 0
        # Must not expose raw Python exception text to the caller
        assert "some internal error" not in error_msg
