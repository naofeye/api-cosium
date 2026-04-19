"""Package analytics_cosium_extras : score, segments, forecast, comparaisons.

Extrait de `analytics_cosium_service.py` pour rester sous 600 L par fichier.
Re-exporte les 8 fonctions publiques pour préserver l'API existante
(`from app.services import analytics_cosium_extras` reste valide).

Sous-modules :
- `_score.py` : `compute_client_score`, `get_top_clients_by_ca`
- `_segments.py` : `compute_dynamic_segments`, `compute_product_mix`
- `_forecast.py` : `get_cashflow_forecast`, `compute_trends`
- `_comparison.py` : `compute_group_comparison`, `compute_best_contact_hour`
"""

from app.services.analytics_cosium_extras._comparison import (
    compute_best_contact_hour,
    compute_group_comparison,
)
from app.services.analytics_cosium_extras._forecast import (
    compute_trends,
    get_cashflow_forecast,
)
from app.services.analytics_cosium_extras._score import (
    compute_client_score,
    get_top_clients_by_ca,
)
from app.services.analytics_cosium_extras._segments import (
    compute_dynamic_segments,
    compute_product_mix,
)

__all__ = [
    "compute_client_score",
    "get_top_clients_by_ca",
    "compute_dynamic_segments",
    "compute_product_mix",
    "get_cashflow_forecast",
    "compute_trends",
    "compute_group_comparison",
    "compute_best_contact_hour",
]
