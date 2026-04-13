"""Period comparison and dashboard aggregation for analytics.

Contains KPI comparison (current vs previous period) and the full
dashboard assembly function.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.analytics import (
    DashboardFull,
    KPIComparison,
)
from app.models import Customer
from app.models.cosium_data import CosiumInvoice
from app.services.analytics_kpi_service import (
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

logger = get_logger("analytics_comparison_service")


def _pct_delta(current: float, previous: float) -> float | None:
    """Calculate percentage change: (current - previous) / previous * 100."""
    if previous == 0:
        return None
    return round((current - previous) / abs(previous) * 100, 1)


def get_kpi_comparison(
    db: Session, tenant_id: int, period_days: int = 7
) -> KPIComparison:
    """Compare current KPIs with previous period.

    Current period: last N days.
    Previous period: N days before that.
    Returns delta percentages for key metrics.
    """
    now = datetime.now(UTC).replace(tzinfo=None)
    current_start = now - timedelta(days=period_days)
    previous_start = current_start - timedelta(days=period_days)

    current_fin = get_financial_kpis(db, tenant_id, date_from=current_start, date_to=now)
    previous_fin = get_financial_kpis(db, tenant_id, date_from=previous_start, date_to=current_start)

    # Cosium invoice counts for current vs previous
    current_invoices = (
        db.scalar(
            select(func.count())
            .select_from(CosiumInvoice)
            .where(
                CosiumInvoice.tenant_id == tenant_id,
                CosiumInvoice.type == "INVOICE",
                CosiumInvoice.invoice_date >= current_start,
                CosiumInvoice.invoice_date <= now,
            )
        )
        or 0
    )
    previous_invoices = (
        db.scalar(
            select(func.count())
            .select_from(CosiumInvoice)
            .where(
                CosiumInvoice.tenant_id == tenant_id,
                CosiumInvoice.type == "INVOICE",
                CosiumInvoice.invoice_date >= previous_start,
                CosiumInvoice.invoice_date < current_start,
            )
        )
        or 0
    )

    # New customers in period
    current_clients = (
        db.scalar(
            select(func.count())
            .select_from(Customer)
            .where(
                Customer.tenant_id == tenant_id,
                Customer.created_at >= current_start,
                Customer.created_at <= now,
            )
        )
        or 0
    )
    previous_clients = (
        db.scalar(
            select(func.count())
            .select_from(Customer)
            .where(
                Customer.tenant_id == tenant_id,
                Customer.created_at >= previous_start,
                Customer.created_at < current_start,
            )
        )
        or 0
    )

    return KPIComparison(
        ca_total_delta=_pct_delta(current_fin.ca_total, previous_fin.ca_total),
        montant_encaisse_delta=_pct_delta(current_fin.montant_encaisse, previous_fin.montant_encaisse),
        reste_a_encaisser_delta=_pct_delta(current_fin.reste_a_encaisser, previous_fin.reste_a_encaisser),
        taux_recouvrement_delta=_pct_delta(current_fin.taux_recouvrement, previous_fin.taux_recouvrement),
        clients_delta=_pct_delta(float(current_clients), float(previous_clients)),
        factures_delta=_pct_delta(float(current_invoices), float(previous_invoices)),
    )


def get_dashboard_full(
    db: Session, tenant_id: int, date_from: datetime | None = None, date_to: datetime | None = None
) -> DashboardFull:
    from app.core.redis_cache import cache_get, cache_set

    # Only use cache when no date filters are applied
    cache_key = f"analytics:dashboard:{tenant_id}"
    if not date_from and not date_to:
        cached = cache_get(cache_key)
        if cached:
            logger.debug("dashboard_full_cache_hit", tenant_id=tenant_id)
            return DashboardFull(**cached)

    # Compute weekly comparison (only for unfiltered dashboard)
    comparison = None
    if not date_from and not date_to:
        try:
            comparison = get_kpi_comparison(db, tenant_id, period_days=7)
        except (SQLAlchemyError, ValueError, TypeError):
            logger.warning("kpi_comparison_failed", tenant_id=tenant_id)

    result = DashboardFull(
        financial=get_financial_kpis(db, tenant_id, date_from, date_to),
        aging=get_aging_balance(db, tenant_id),
        payers=get_payer_performance(db, tenant_id),
        operational=get_operational_kpis(db, tenant_id),
        commercial=get_commercial_kpis(db, tenant_id),
        marketing=get_marketing_kpis(db, tenant_id),
        cosium=get_cosium_kpis(db, tenant_id),
        cosium_counts=get_cosium_counts(db, tenant_id),
        cosium_ca_par_mois=get_cosium_ca_par_mois(db, tenant_id),
        comparison=comparison,
    )

    if not date_from and not date_to:
        cache_set(cache_key, result.model_dump(), ttl=300)

    return result
