"""Service for admin user management (CRUD)."""

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.core.logging import get_logger
from app.domain.schemas.admin_users import AdminUserCreate, AdminUserResponse, AdminUserUpdate
from app.models import TenantUser, User
from app.security import hash_password
from app.services import audit_service

logger = get_logger("admin_user_service")


def list_users(db: Session, tenant_id: int) -> list[AdminUserResponse]:
    """List all users for a given tenant."""
    tenant_users = (
        db.query(TenantUser)
        .filter(TenantUser.tenant_id == tenant_id)
        .all()
    )
    result: list[AdminUserResponse] = []
    for tu in tenant_users:
        user = db.query(User).filter(User.id == tu.user_id).first()
        if user:
            result.append(
                AdminUserResponse(
                    id=user.id,
                    email=user.email,
                    role=tu.role,
                    is_active=tu.is_active and user.is_active,
                    created_at=user.created_at,
                    last_login_at=None,
                )
            )
    return result


def create_user(
    db: Session, tenant_id: int, payload: AdminUserCreate, admin_user_id: int
) -> AdminUserResponse:
    """Create a new user and associate to the tenant."""
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        # Check if already in this tenant
        tu = (
            db.query(TenantUser)
            .filter(
                TenantUser.user_id == existing.id,
                TenantUser.tenant_id == tenant_id,
            )
            .first()
        )
        if tu:
            raise BusinessError("Un utilisateur avec cet email existe deja dans ce magasin.")
        # Add existing user to tenant
        new_tu = TenantUser(
            user_id=existing.id,
            tenant_id=tenant_id,
            role=payload.role,
            is_active=True,
        )
        db.add(new_tu)
        db.commit()
        audit_service.log_action(
            db, tenant_id, admin_user_id, "create", "tenant_user", new_tu.id
        )
        logger.info(
            "user_added_to_tenant",
            user_id=existing.id,
            tenant_id=tenant_id,
            role=payload.role,
        )
        return AdminUserResponse(
            id=existing.id,
            email=existing.email,
            role=payload.role,
            is_active=True,
            created_at=existing.created_at,
            last_login_at=None,
        )

    # Create new user
    new_user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(new_user)
    db.flush()

    new_tu = TenantUser(
        user_id=new_user.id,
        tenant_id=tenant_id,
        role=payload.role,
        is_active=True,
    )
    db.add(new_tu)
    db.commit()
    db.refresh(new_user)

    audit_service.log_action(
        db, tenant_id, admin_user_id, "create", "user", new_user.id
    )
    logger.info(
        "user_created",
        user_id=new_user.id,
        tenant_id=tenant_id,
        role=payload.role,
    )
    return AdminUserResponse(
        id=new_user.id,
        email=new_user.email,
        role=payload.role,
        is_active=True,
        created_at=new_user.created_at,
        last_login_at=None,
    )


def update_user(
    db: Session,
    tenant_id: int,
    user_id: int,
    payload: AdminUserUpdate,
    admin_user_id: int,
) -> AdminUserResponse:
    """Update a user's role or active status within the tenant."""
    tu = (
        db.query(TenantUser)
        .filter(
            TenantUser.user_id == user_id,
            TenantUser.tenant_id == tenant_id,
        )
        .first()
    )
    if not tu:
        raise NotFoundError("Utilisateur", user_id)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("Utilisateur", user_id)

    if payload.role is not None:
        tu.role = payload.role
    if payload.is_active is not None:
        tu.is_active = payload.is_active

    db.commit()
    db.refresh(tu)

    audit_service.log_action(
        db, tenant_id, admin_user_id, "update", "tenant_user", tu.id
    )
    logger.info(
        "user_updated",
        user_id=user_id,
        tenant_id=tenant_id,
        changes=payload.model_dump(exclude_none=True),
    )
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        role=tu.role,
        is_active=tu.is_active and user.is_active,
        created_at=user.created_at,
        last_login_at=None,
    )


def deactivate_user(
    db: Session, tenant_id: int, user_id: int, admin_user_id: int
) -> AdminUserResponse:
    """Deactivate a user within the tenant (soft delete)."""
    if user_id == admin_user_id:
        raise BusinessError("Vous ne pouvez pas desactiver votre propre compte.")

    tu = (
        db.query(TenantUser)
        .filter(
            TenantUser.user_id == user_id,
            TenantUser.tenant_id == tenant_id,
        )
        .first()
    )
    if not tu:
        raise NotFoundError("Utilisateur", user_id)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("Utilisateur", user_id)

    tu.is_active = False
    db.commit()

    audit_service.log_action(
        db, tenant_id, admin_user_id, "deactivate", "tenant_user", tu.id
    )
    logger.info("user_deactivated", user_id=user_id, tenant_id=tenant_id)
    return AdminUserResponse(
        id=user.id,
        email=user.email,
        role=tu.role,
        is_active=False,
        created_at=user.created_at,
        last_login_at=None,
    )
