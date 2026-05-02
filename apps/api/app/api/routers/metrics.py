"""Endpoint Prometheus /metrics — exposition format texte standard.

Auth :
- Si `METRICS_TOKEN` est defini : exige `Authorization: Bearer <token>`.
- Sinon en dev/test : pas d'auth (scrape local).
- Sinon en prod/staging : refuse 403 (defense en profondeur si nginx fait defaut).

Stack monitoring : Prometheus scrape ce endpoint toutes les 30s.
"""
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import Customer, Tenant, User
from app.models.cosium_data import CosiumInvoice
from app.models.notification import ActionItem

router = APIRouter(prefix="/api/v1", tags=["metrics"])


def _check_metrics_auth(authorization: str | None = Header(default=None)) -> None:
    """Garde-fou bearer pour /metrics.

    En prod/staging :
    - Si METRICS_TOKEN configure → exige `Authorization: Bearer <token>`
      (comparaison constant-time).
    - Si METRICS_TOKEN vide → 403 (refus par defaut, evite l'exposition silencieuse
      derriere nginx mal configure).

    En dev/test : ouvert sans token pour ne pas bloquer le scrape local.
    """
    expected = settings.metrics_token
    is_protected_env = settings.app_env in ("production", "staging")

    if not expected:
        if is_protected_env:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Metrics endpoint protected: METRICS_TOKEN must be configured",
            )
        return  # dev/test ouvert

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    provided = authorization[len("Bearer ") :].strip()
    if not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid metrics token",
        )


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
    description=(
        "Expose les compteurs business pour scraping Prometheus. "
        "Auth bearer requise via METRICS_TOKEN en prod/staging."
    ),
    dependencies=[Depends(_check_metrics_auth)],
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

    # Metrics MFA (securite) — User deja importe en haut
    users_mfa_enabled = db.scalar(
        select(func.count()).select_from(User).where(User.totp_enabled.is_(True))
    ) or 0
    output.append(_format_metric(
        "optiflow_users_mfa_enabled", users_mfa_enabled,
        "Nombre d'utilisateurs avec MFA/TOTP active",
    ))

    # Metrics sync Cosium (age dernier sync par tenant) — CosiumInvoice deja importe
    last_sync = db.scalar(
        select(func.max(CosiumInvoice.synced_at))
    )
    if last_sync:
        import time
        age_seconds = int(time.time() - last_sync.timestamp())
        output.append(_format_metric(
            "optiflow_cosium_last_sync_age_seconds", age_seconds,
            "Age en secondes du dernier sync Cosium (invoice)",
        ))

    # Action items resolus sur les 7 derniers jours (velocite)
    from datetime import UTC, datetime, timedelta
    week_ago = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=7)
    resolved_7d = db.scalar(
        select(func.count()).select_from(ActionItem).where(
            ActionItem.status == "resolved",
            ActionItem.created_at >= week_ago,
        )
    ) or 0
    output.append(_format_metric(
        "optiflow_action_items_resolved_7d", resolved_7d,
        "Action items resolus sur les 7 derniers jours",
    ))

    return Response(content="".join(output), media_type="text/plain; version=0.0.4")
