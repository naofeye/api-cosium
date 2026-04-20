"""Unit tests for batch_processing_service.

Tests process_batch() and prepare_batch_pec() directly against the service layer,
using the in-memory SQLite db fixture and mocking consolidation/pec_preparation.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import NotFoundError
from app.domain.schemas.consolidation import ConsolidatedClientProfile
from app.models.batch_operation import BatchOperation
from app.models.client import Customer
from app.models.tenant import Tenant
from app.repositories import batch_operation_repo
from app.services import batch_processing_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _seed_batch(db, tenant_id: int, customer_ids: list[int]) -> BatchOperation:
    """Create a batch + items in 'en_attente' status."""
    batch = batch_operation_repo.create_batch(
        db,
        tenant_id=tenant_id,
        marketing_code="TEST_CODE",
        label="Test batch",
        created_by=1,
        total_clients=len(customer_ids),
    )
    for cid in customer_ids:
        batch_operation_repo.create_item(
            db,
            tenant_id=tenant_id,
            batch_id=batch.id,
            customer_id=cid,
        )
    db.commit()
    return batch


def _seed_customers(db, tenant_id: int, count: int = 3) -> list[int]:
    """Create `count` customers and return their ids."""
    ids = []
    for i in range(count):
        c = Customer(
            tenant_id=tenant_id,
            first_name=f"Prenom{i}",
            last_name=f"Nom{i}",
        )
        db.add(c)
        db.flush()
        ids.append(c.id)
    db.commit()
    return ids


def _good_profile(score: float = 85.0) -> ConsolidatedClientProfile:
    return ConsolidatedClientProfile(score_completude=score, alertes=[])


def _profile_with_errors(errors: int = 1, warnings: int = 0) -> ConsolidatedClientProfile:
    from app.domain.schemas.consolidation import ConsolidationAlert

    alertes = [
        ConsolidationAlert(field="ssn", message="Manquant", severity="error")
        for _ in range(errors)
    ] + [
        ConsolidationAlert(field="email", message="Vide", severity="warning")
        for _ in range(warnings)
    ]
    return ConsolidatedClientProfile(score_completude=40.0, alertes=alertes)


# ---------------------------------------------------------------------------
# Tests — process_batch
# ---------------------------------------------------------------------------

@patch("app.services.batch_processing_service.consolidation_service.consolidate_client_for_pec")
def test_process_batch_all_items_succeed(mock_consolidate, db, default_tenant: Tenant):
    """All items transition to 'pret' when score >= 70 and no errors."""
    customer_ids = _seed_customers(db, default_tenant.id, count=3)
    batch = _seed_batch(db, default_tenant.id, customer_ids)

    mock_consolidate.return_value = _good_profile(score=90.0)

    result = batch_processing_service.process_batch(db, default_tenant.id, batch.id, user_id=1)

    assert result.status == "termine"
    assert result.clients_prets == 3
    assert result.clients_incomplets == 0
    assert result.clients_erreur == 0
    assert mock_consolidate.call_count == 3


@patch("app.services.batch_processing_service.consolidation_service.consolidate_client_for_pec")
def test_process_batch_one_item_fails_others_continue(mock_consolidate, db, default_tenant: Tenant):
    """A ValueError for one item is caught; remaining items are still processed."""
    customer_ids = _seed_customers(db, default_tenant.id, count=3)
    batch = _seed_batch(db, default_tenant.id, customer_ids)

    mock_consolidate.side_effect = [
        _good_profile(90.0),
        ValueError("Consolidation impossible"),
        _good_profile(90.0),
    ]

    result = batch_processing_service.process_batch(db, default_tenant.id, batch.id, user_id=1)

    assert result.status == "termine"
    assert result.clients_prets == 2
    assert result.clients_erreur == 1

    # Verify that the failed item carries the error message in db
    items = batch_operation_repo.get_items_by_batch(db, batch.id)
    errored = [i for i in items if i.status == "erreur"]
    assert len(errored) == 1
    assert "Consolidation impossible" in errored[0].error_message


@patch("app.services.batch_processing_service.consolidation_service.consolidate_client_for_pec")
def test_process_batch_low_score_marks_incomplet(mock_consolidate, db, default_tenant: Tenant):
    """Items with score < 70 and no errors are marked 'incomplet'."""
    customer_ids = _seed_customers(db, default_tenant.id, count=2)
    batch = _seed_batch(db, default_tenant.id, customer_ids)

    mock_consolidate.return_value = _good_profile(score=50.0)

    result = batch_processing_service.process_batch(db, default_tenant.id, batch.id, user_id=1)

    assert result.status == "termine"
    assert result.clients_incomplets == 2
    assert result.clients_prets == 0


@patch("app.services.batch_processing_service.consolidation_service.consolidate_client_for_pec")
def test_process_batch_errors_with_warnings_marks_conflit(mock_consolidate, db, default_tenant: Tenant):
    """Items with both errors and warnings are marked 'conflit'."""
    customer_ids = _seed_customers(db, default_tenant.id, count=1)
    batch = _seed_batch(db, default_tenant.id, customer_ids)

    mock_consolidate.return_value = _profile_with_errors(errors=1, warnings=1)

    result = batch_processing_service.process_batch(db, default_tenant.id, batch.id, user_id=1)

    assert result.status == "termine"
    assert result.clients_en_conflit == 1


@patch("app.services.batch_processing_service.consolidation_service.consolidate_client_for_pec")
def test_process_batch_errors_only_marks_incomplet(mock_consolidate, db, default_tenant: Tenant):
    """Items with errors but no warnings are marked 'incomplet'."""
    customer_ids = _seed_customers(db, default_tenant.id, count=1)
    batch = _seed_batch(db, default_tenant.id, customer_ids)

    mock_consolidate.return_value = _profile_with_errors(errors=1, warnings=0)

    result = batch_processing_service.process_batch(db, default_tenant.id, batch.id, user_id=1)

    assert result.status == "termine"
    assert result.clients_incomplets == 1
    assert result.clients_en_conflit == 0


def test_process_batch_empty_batch(db, default_tenant: Tenant):
    """Empty batch (no items) completes immediately with all-zero stats."""
    batch = _seed_batch(db, default_tenant.id, customer_ids=[])

    result = batch_processing_service.process_batch(db, default_tenant.id, batch.id, user_id=1)

    assert result.status == "termine"
    assert result.clients_prets == 0
    assert result.clients_erreur == 0


def test_process_batch_not_found_raises(db, default_tenant: Tenant):
    """NotFoundError raised when batch_id does not exist."""
    with pytest.raises(NotFoundError):
        batch_processing_service.process_batch(db, default_tenant.id, batch_id=99999, user_id=1)


@patch("app.services.batch_processing_service.consolidation_service.consolidate_client_for_pec")
def test_process_batch_progress_tracking(mock_consolidate, db, default_tenant: Tenant):
    """Batch status is updated to 'en_cours' during processing, then 'termine'."""
    customer_ids = _seed_customers(db, default_tenant.id, count=2)
    batch = _seed_batch(db, default_tenant.id, customer_ids)

    mock_consolidate.return_value = _good_profile()

    result = batch_processing_service.process_batch(db, default_tenant.id, batch.id, user_id=1)

    # Final state must be 'termine', not 'en_cours'
    assert result.status == "termine"
    assert result.completed_at is not None


# ---------------------------------------------------------------------------
# Tests — prepare_batch_pec
# ---------------------------------------------------------------------------

@patch("app.services.batch_processing_service.pec_preparation_service.prepare_pec")
@patch("app.services.batch_processing_service.consolidation_service.consolidate_client_for_pec")
def test_prepare_batch_pec_creates_pec_for_pret_items(
    mock_consolidate, mock_prepare, db, default_tenant: Tenant
):
    """prepare_batch_pec calls prepare_pec once per 'pret' item."""
    customer_ids = _seed_customers(db, default_tenant.id, count=2)
    batch = _seed_batch(db, default_tenant.id, customer_ids)

    # Process first to mark items 'pret'
    mock_consolidate.return_value = _good_profile(90.0)
    batch_processing_service.process_batch(db, default_tenant.id, batch.id, user_id=1)

    mock_pec = MagicMock()
    mock_pec.id = 42
    mock_prepare.return_value = mock_pec

    result = batch_processing_service.prepare_batch_pec(db, default_tenant.id, batch.id, user_id=1)

    assert result.prepared == 2
    assert result.errors == 0
    assert mock_prepare.call_count == 2


@patch("app.services.batch_processing_service.pec_preparation_service.prepare_pec")
@patch("app.services.batch_processing_service.consolidation_service.consolidate_client_for_pec")
def test_prepare_batch_pec_handles_individual_errors(
    mock_consolidate, mock_prepare, db, default_tenant: Tenant
):
    """prepare_batch_pec continues when one PEC preparation fails."""
    customer_ids = _seed_customers(db, default_tenant.id, count=3)
    batch = _seed_batch(db, default_tenant.id, customer_ids)

    mock_consolidate.return_value = _good_profile(90.0)
    batch_processing_service.process_batch(db, default_tenant.id, batch.id, user_id=1)

    good_pec = MagicMock()
    good_pec.id = 99
    mock_prepare.side_effect = [good_pec, ValueError("PEC impossible"), good_pec]

    result = batch_processing_service.prepare_batch_pec(db, default_tenant.id, batch.id, user_id=1)

    assert result.prepared == 2
    assert result.errors == 1


def test_prepare_batch_pec_not_found_raises(db, default_tenant: Tenant):
    """NotFoundError raised for non-existent batch."""
    with pytest.raises(NotFoundError):
        batch_processing_service.prepare_batch_pec(db, default_tenant.id, batch_id=99999, user_id=1)


@patch("app.services.batch_processing_service.pec_preparation_service.prepare_pec")
@patch("app.services.batch_processing_service.consolidation_service.consolidate_client_for_pec")
def test_prepare_batch_pec_skips_non_pret_items(
    mock_consolidate, mock_prepare, db, default_tenant: Tenant
):
    """prepare_batch_pec ignores items that are not in 'pret' status."""
    customer_ids = _seed_customers(db, default_tenant.id, count=3)
    batch = _seed_batch(db, default_tenant.id, customer_ids)

    # Two pret, one incomplet
    mock_consolidate.side_effect = [
        _good_profile(90.0),
        _good_profile(90.0),
        _good_profile(score=40.0),  # will be 'incomplet'
    ]
    batch_processing_service.process_batch(db, default_tenant.id, batch.id, user_id=1)

    good_pec = MagicMock()
    good_pec.id = 55
    mock_prepare.return_value = good_pec

    result = batch_processing_service.prepare_batch_pec(db, default_tenant.id, batch.id, user_id=1)

    assert result.prepared == 2
    assert mock_prepare.call_count == 2
