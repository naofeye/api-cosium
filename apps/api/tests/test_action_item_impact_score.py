"""Tests calcul impact_score deterministe."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.services._action_items.impact_score import (
    PRIORITY_BASE,
    compute_impact_score,
)


def test_priority_base_alone():
    assert compute_impact_score(priority="critical") == 100
    assert compute_impact_score(priority="high") == 70
    assert compute_impact_score(priority="medium") == 40
    assert compute_impact_score(priority="low") == 10


def test_unknown_priority_defaults_medium():
    assert compute_impact_score(priority="unknown") == 40


def test_montant_boost_logarithmic():
    # log10(100) = 2 -> 100
    s = compute_impact_score(priority="medium", amount_eur=100)
    assert s == 40 + 100  # 140

    # log10(10000) = 4 -> 200 saturated
    s = compute_impact_score(priority="medium", amount_eur=10000)
    assert s == 40 + 200  # 240

    # Saturation
    s = compute_impact_score(priority="medium", amount_eur=1_000_000)
    assert s == 40 + 200  # capped


def test_recency_boost_decreases():
    now = datetime.now(UTC)
    s_today = compute_impact_score(priority="low", reference_date=now)
    s_2w = compute_impact_score(priority="low", reference_date=now - timedelta(days=14))
    s_2m = compute_impact_score(priority="low", reference_date=now - timedelta(days=60))
    s_old = compute_impact_score(priority="low", reference_date=now - timedelta(days=200))

    assert s_today == 10 + 50  # 60
    assert s_2w == 10 + 30
    assert s_2m == 10 + 10
    assert s_old == 10  # base only


def test_combined_max():
    """High + montant 1M + today < total max attendu."""
    s = compute_impact_score(
        priority="critical",
        amount_eur=10000,
        reference_date=datetime.now(UTC),
    )
    assert s == 100 + 200 + 50  # 350


def test_negative_amount_ignored():
    s = compute_impact_score(priority="medium", amount_eur=-100)
    assert s == 40


def test_zero_amount_no_boost():
    s = compute_impact_score(priority="medium", amount_eur=0)
    assert s == 40
