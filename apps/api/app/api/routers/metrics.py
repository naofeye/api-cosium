"""Endpoint Prometheus /metrics — exposition format texte standard.

Pas d'authentification (le bind 127.0.0.1 + nginx restreignent l'acces).
Stack stack monitoring : Prometheus scrape ce endpoint toutes les 30s.
"""
from fastapi import APIRouter, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from fastapi import Depends

from app.db.session import get_db
from app.models import Customer, Tenant, User
from app.models.cosium_data import CosiumInvoice
from app.models.notification import ActionItem

router = APIRouter(prefix="/api/v1", tags=["metrics"])


def _format_metric(name: str, value: float, help_text: str = "", labels: dict | None = None) -> str:
    """Format Prometheus exposition (sans dependre de prometheus_client)."""
    lines = []
    if help_text:
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} gauge")
    if labels:
        labels_str = ",".join(f'{k}="{v}"' for k, v in labels.items())
        lines.append(f"{name}{{{labels_str}}} {value}")
    else:
        lines.append(f"{name} {value}")
    return "\n".join(lines) + "\n"


@router.get(
    "/metrics",
    summary="Metrics Prometheus (format texte)",
    description="Expose les compteurs business pour scraping Prometheus. Pas d'auth (bind 127.0.0.1).",
)
def prometheus_metrics(db: Session = Depends(get_db)) -> Response:
    """Counters globaux (multi-tenant) pour observabilite."""
    output = []

    # Compteurs globaux
    total_tenants = db.scalar(select(func.count()).select_from(Tenant)) or 0
    total_users = db.scalar(select(func.count()).select_from(User)) or 0
    total_active_users = db.scalar(
        select(func.count()).select_from(User).where(User.is_active.is_(True))
    ) or 0
    total_customers = db.scalar(
        select(func.count()).select_from(Customer).where(Customer.deleted_at.is_(None))
    ) or 0

    output.append(_format_metric(
        "optiflow_tenants_total", total_tenants,
        "Nombre total de tenants (magasins) actifs et inactifs",
    ))
    output.append(_format_metric(
        "optiflow_users_total", total_users,
        "Nombre total d'utilisateurs (toutes versions confondues)",
    ))
    output.append(_format_metric(
        "optiflow_users_active", total_active_users,
        "Nombre d'utilisateurs actifs",
    ))
    output.append(_format_metric(
        "optiflow_customers_total", total_customers,
        "Nombre total de clients (non soft-deleted)",
    ))

    # Metrics Cosium invoices
    total_cosium_invoices = db.scalar(
        select(func.count()).select_from(CosiumInvoice).where(CosiumInvoice.type == "INVOICE")
    ) or 0
    total_outstanding = float(
        db.scalar(
            select(func.coalesce(func.sum(CosiumInvoice.outstanding_balance), 0))
            .where(CosiumInvoice.type == "INVOICE", CosiumInvoice.outstanding_balance > 0)
        )
        or 0
    )
    output.append(_format_metric(
        "optiflow_cosium_invoices_total", total_cosium_invoices,
        "Nombre total de factures Cosium synchronisees",
    ))
    output.append(_format_metric(
        "optiflow_outstanding_balance_eur", round(total_outstanding, 2),
        "Encours impaye total (EUR) sur l'ensemble des factures Cosium",
    ))

    # Metrics action items (par statut)
    pending_count = db.scalar(
        select(func.count()).select_from(ActionItem).where(ActionItem.status == "pending")
    ) or 0
    output.append(_format_metric(
        "optiflow_action_items_pending", pending_count,
        "Nombre d'action items en attente sur l'ensemble des tenants",
    ))

    # Action items par type (label)
    types_rows = db.execute(
        select(ActionItem.type, func.count())
        .where(ActionItem.status == "pending")
        .group_by(ActionItem.type)
    ).all()
    if types_rows:
        output.append("# HELP optiflow_action_items_by_type Action items en attente, par type\n")
        output.append("# TYPE optiflow_action_items_by_type gauge\n")
        for type_name, count in types_rows:
            output.append(f'optiflow_action_items_by_type{{type="{type_name}"}} {count}\n')

    return Response(content="".join(output), media_type="text/plain; version=0.0.4")
