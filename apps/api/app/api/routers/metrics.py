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

    return Response(content="".join(output), media_type="text/plain; version=0.0.4")
