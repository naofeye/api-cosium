"""Tests for collection prioritizer module."""

from unittest.mock import patch

from app.services.collection_prioritizer import (
    _estimate_recovery_probability,
    _recommend_action,
    prioritize_overdue,
)

# --- _estimate_recovery_probability tests ---

def test_recovery_probability_low_days():
    assert _estimate_recovery_probability(10) == 0.90


def test_recovery_probability_medium_days():
    assert _estimate_recovery_probability(45) == 0.70


def test_recovery_probability_high_days():
    # 100 days falls in the 91-180 bracket
    assert _estimate_recovery_probability(100) == 0.25


def test_recovery_probability_very_old():
    assert _estimate_recovery_probability(400) == 0.05


def test_recovery_probability_boundary_30():
    assert _estimate_recovery_probability(30) == 0.90


def test_recovery_probability_boundary_60():
    assert _estimate_recovery_probability(60) == 0.70


# --- _recommend_action tests ---

def test_recommend_action_client_email():
    assert _recommend_action(10, "client") == "email"


def test_recommend_action_client_sms():
    assert _recommend_action(20, "client") == "sms"


def test_recommend_action_client_courrier():
    assert _recommend_action(45, "client") == "courrier"


def test_recommend_action_client_telephone():
    assert _recommend_action(90, "client") == "telephone"


def test_recommend_action_mutuelle_email():
    assert _recommend_action(10, "mutuelle") == "email"


def test_recommend_action_mutuelle_courrier():
    assert _recommend_action(30, "mutuelle") == "courrier"


def test_recommend_action_mutuelle_telephone():
    assert _recommend_action(60, "mutuelle") == "telephone"


def test_recommend_action_secu_same_as_mutuelle():
    assert _recommend_action(10, "secu") == "email"
    assert _recommend_action(30, "secu") == "courrier"
    assert _recommend_action(60, "secu") == "telephone"


# --- prioritize_overdue tests ---

@patch("app.services.collection_prioritizer.reminder_repo")
def test_prioritize_overdue_empty(mock_repo):
    """Empty overdue list returns empty."""
    mock_repo.get_all_overdue.return_value = []
    result = prioritize_overdue(None, tenant_id=1)
    assert result == []


@patch("app.services.collection_prioritizer.reminder_repo")
def test_prioritize_overdue_score_increases_with_amount(mock_repo):
    """Higher amount should produce higher score, all else equal."""
    mock_repo.get_all_overdue.return_value = [
        {"entity_type": "facture", "entity_id": 1, "customer_name": "A",
         "payer_type": "client", "amount": 100.0, "days_overdue": 30},
        {"entity_type": "facture", "entity_id": 2, "customer_name": "B",
         "payer_type": "client", "amount": 500.0, "days_overdue": 30},
    ]
    result = prioritize_overdue(None, tenant_id=1)
    # Higher amount item should have higher score and come first
    assert result[0].entity_id == 2
    assert result[0].score > result[1].score


@patch("app.services.collection_prioritizer.reminder_repo")
def test_prioritize_overdue_score_increases_with_days(mock_repo):
    """More days overdue should increase score (age_factor), all else equal."""
    mock_repo.get_all_overdue.return_value = [
        {"entity_type": "facture", "entity_id": 1, "customer_name": "A",
         "payer_type": "client", "amount": 200.0, "days_overdue": 10},
        {"entity_type": "facture", "entity_id": 2, "customer_name": "B",
         "payer_type": "client", "amount": 200.0, "days_overdue": 50},
    ]
    result = prioritize_overdue(None, tenant_id=1)
    # Both have same amount, but days_overdue=50 has higher age_factor
    scores = {r.entity_id: r.score for r in result}
    assert scores[2] > scores[1]


@patch("app.services.collection_prioritizer.reminder_repo")
def test_prioritize_overdue_sorted_by_score_desc(mock_repo):
    """Results should be sorted by score descending."""
    mock_repo.get_all_overdue.return_value = [
        {"entity_type": "facture", "entity_id": 1, "customer_name": "A",
         "payer_type": "client", "amount": 50.0, "days_overdue": 5},
        {"entity_type": "facture", "entity_id": 2, "customer_name": "B",
         "payer_type": "client", "amount": 1000.0, "days_overdue": 20},
        {"entity_type": "pec", "entity_id": 3, "customer_name": "C",
         "payer_type": "mutuelle", "amount": 300.0, "days_overdue": 60},
    ]
    result = prioritize_overdue(None, tenant_id=1)
    scores = [r.score for r in result]
    assert scores == sorted(scores, reverse=True)


@patch("app.services.collection_prioritizer.reminder_repo")
def test_prioritize_overdue_action_field(mock_repo):
    """Each item should have a recommended action."""
    mock_repo.get_all_overdue.return_value = [
        {"entity_type": "facture", "entity_id": 1, "customer_name": "A",
         "payer_type": "client", "amount": 100.0, "days_overdue": 10},
    ]
    result = prioritize_overdue(None, tenant_id=1)
    assert result[0].action == "email"
