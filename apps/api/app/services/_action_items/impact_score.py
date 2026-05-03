"""Calcul deterministe d'impact_score pour priorisation action items.

Combine priority categorielle + montant financier + recence pour produire
un entier triable. Pas d'appel API IA : 100% local, deterministe.

Voir ADR-0009 (impact_score deterministic prioritization).
"""
from __future__ import annotations

import math
from datetime import UTC, datetime

PRIORITY_BASE = {
    "critical": 100,
    "high": 70,
    "medium": 40,
    "low": 10,
}


def compute_impact_score(
    *,
    priority: str,
    amount_eur: float | None = None,
    reference_date: datetime | None = None,
) -> int:
    """Score 0-350 entier. Plus haut = priorite plus forte.

    Args:
        priority: 'critical' | 'high' | 'medium' | 'low'
        amount_eur: montant financier associe (facture en retard, devis,
            valeur client). 0 ou None = pas de boost.
        reference_date: date de reference pour le calcul de recence
            (typiquement la date d'echeance facture, naissance client,
            etc.). Aujourd'hui si None.

    Returns:
        Entier non-negatif, max ~350.
    """
    base = PRIORITY_BASE.get(priority, PRIORITY_BASE["medium"])

    # Montant factor : log10(amount), saturated a 200
    montant_factor = 0
    if amount_eur and amount_eur > 0:
        # log10(100) = 2 -> 100, log10(10000) = 4 -> 200
        montant_factor = min(int(math.log10(max(amount_eur, 1)) * 50), 200)

    # Recency factor : plus c'est vieux/imminent, plus c'est urgent
    recency_factor = 0
    if reference_date is not None:
        now = datetime.now(UTC).replace(tzinfo=None)
        ref = reference_date.replace(tzinfo=None) if reference_date.tzinfo else reference_date
        days_diff = abs((now - ref).days)
        if days_diff < 7:
            recency_factor = 50
        elif days_diff < 30:
            recency_factor = 30
        elif days_diff < 90:
            recency_factor = 10

    return base + montant_factor + recency_factor
