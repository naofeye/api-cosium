"""Queries internes utilisees par auth_service (tenants accessibles, role admin, MFA enforcement)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Tenant, TenantUser
from app.repositories import tenant_user_repo


def get_user_tenants(db: Session, user_id: int) -> list[dict]:
    """Retourne tous les tenants actifs auxquels l'user a acces.

    Optimisation N+1 : un seul JOIN TenantUser x Tenant au lieu de N queries.
    """
    rows = db.execute(
        select(Tenant.id, Tenant.name, Tenant.slug, TenantUser.role)
        .join(TenantUser, TenantUser.tenant_id == Tenant.id)
        .where(
            TenantUser.user_id == user_id,
            TenantUser.is_active.is_(True),
            Tenant.is_active.is_(True),
        )
    ).all()
    return [{"id": r.id, "name": r.name, "slug": r.slug, "role": r.role} for r in rows]


def is_group_admin(db: Session, user_id: int) -> bool:
    rows = tenant_user_repo.list_admin_active_by_user(db, user_id)
    return len(rows) > 1


def user_must_have_mfa(db: Session, user_id: int) -> bool:
    """True si l'user est admin dans au moins un tenant avec require_admin_mfa=True.

    Implique que l'user doit avoir MFA active pour se connecter.
    """
    rows = db.execute(
        select(Tenant.require_admin_mfa)
        .join(TenantUser, TenantUser.tenant_id == Tenant.id)
        .where(
            TenantUser.user_id == user_id,
            TenantUser.is_active.is_(True),
            TenantUser.role == "admin",
            Tenant.require_admin_mfa.is_(True),
        )
        .limit(1)
    ).first()
    return rows is not None
