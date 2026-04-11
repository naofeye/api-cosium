"""Admin metrics and data quality service — business logic extracted from admin_health router."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AuditLog, Case, Customer, Facture, Payment


def get_tenant_metrics(db: Session, tenant_id: int) -> dict:
    """Compute tenant-scoped metrics: totals and recent activity."""
    from app.models import TenantUser

    one_hour_ago = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)

    total_users = db.scalar(
        select(func.count()).select_from(TenantUser).where(
            TenantUser.tenant_id == tenant_id, TenantUser.is_active.is_(True)
        )
    ) or 0
    total_clients = db.scalar(select(func.count()).select_from(Customer).where(Customer.tenant_id == tenant_id)) or 0
    total_cases = db.scalar(select(func.count()).select_from(Case).where(Case.tenant_id == tenant_id)) or 0
    total_factures = db.scalar(select(func.count()).select_from(Facture).where(Facture.tenant_id == tenant_id)) or 0
    total_payments = db.scalar(select(func.count()).select_from(Payment).where(Payment.tenant_id == tenant_id)) or 0

    recent_actions = (
        db.scalar(
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.tenant_id == tenant_id, AuditLog.created_at >= one_hour_ago)
        )
        or 0
    )

    active_users = (
        db.scalar(
            select(func.count(func.distinct(AuditLog.user_id))).where(
                AuditLog.tenant_id == tenant_id, AuditLog.created_at >= one_hour_ago
            )
        )
        or 0
    )

    return {
        "totals": {
            "users": total_users,
            "clients": total_clients,
            "dossiers": total_cases,
            "factures": total_factures,
            "paiements": total_payments,
        },
        "activity": {
            "actions_last_hour": recent_actions,
            "active_users_last_hour": active_users,
        },
    }


def get_entity_quality(db: Session, model: type, tenant_id: int) -> dict:
    """Compute link stats (total, linked, orphan, link_rate) for a Cosium data model."""
    total = db.scalar(
        select(func.count()).select_from(model).where(model.tenant_id == tenant_id)
    ) or 0
    linked = db.scalar(
        select(func.count()).select_from(model).where(
            model.tenant_id == tenant_id,
            model.customer_id.isnot(None),
        )
    ) or 0
    orphan = total - linked
    link_rate = round((linked / total) * 100, 1) if total > 0 else 0.0
    return {"total": total, "linked": linked, "orphan": orphan, "link_rate": link_rate}
