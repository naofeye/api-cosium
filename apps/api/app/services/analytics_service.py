"""Analytics service facade.

Delegates to sub-modules for individual KPI calculations and comparisons:
- analytics_kpi_service: individual KPI computation functions
- analytics_comparison_service: period comparisons and dashboard assembly

All public functions are re-exported here for backward compatibility.
"""

from app.services.analytics_comparison_service import (  # noqa: F401
    get_dashboard_full,
    get_kpi_comparison,
)
from app.services.analytics_kpi_service import (  # noqa: F401
    get_aging_balance,
    get_commercial_kpis,
    get_cosium_ca_par_mois,
    get_cosium_counts,
    get_cosium_kpis,
    get_financial_kpis,
    get_marketing_kpis,
    get_operational_kpis,
    get_payer_performance,
)
