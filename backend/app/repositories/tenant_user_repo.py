"""Repository for TenantUser queries."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TenantUser


def get_by_user_and_tenant(db: Session, user_id: int, tenant_id: int) -> TenantUser | None:
    return db.scalars(
        select(TenantUser).where(
            TenantUser.user_id == user_id,
            TenantUser.tenant_id == tenant_id,
        )
    ).first()


def get_active_by_user_and_tenant(db: Session, user_id: int, tenant_id: int) -> TenantUser | None:
    return db.scalars(
        select(TenantUser).where(
            TenantUser.user_id == user_id,
            TenantUser.tenant_id == tenant_id,
            TenantUser.is_active.is_(True),
        )
    ).first()


def list_by_tenant(db: Session, tenant_id: int) -> list[TenantUser]:
    return list(
        db.scalars(
            select(TenantUser).where(TenantUser.tenant_id == tenant_id)
        ).all()
    )


def list_active_by_user(db: Session, user_id: int) -> list[TenantUser]:
    return list(
        db.scalars(
            select(TenantUser).where(
                TenantUser.user_id == user_id,
                TenantUser.is_active.is_(True),
            )
        ).all()
    )


def list_admin_active_by_user(db: Session, user_id: int) -> list[TenantUser]:
    return list(
        db.scalars(
            select(TenantUser).where(
                TenantUser.user_id == user_id,
                TenantUser.role == "admin",
                TenantUser.is_active.is_(True),
            )
        ).all()
    )


def get_first_active_by_user(db: Session, user_id: int) -> TenantUser | None:
    return db.scalars(
        select(TenantUser).where(
            TenantUser.user_id == user_id,
            TenantUser.is_active.is_(True),
        )
    ).first()


def create(
    db: Session, user_id: int, tenant_id: int, role: str, is_active: bool = True
) -> TenantUser:
    tu = TenantUser(user_id=user_id, tenant_id=tenant_id, role=role, is_active=is_active)
    db.add(tu)
    db.flush()
    return tu
