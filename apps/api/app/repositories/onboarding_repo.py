"""Repository for onboarding operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer, Organization, Tenant, TenantUser, User

# Whitelists mass-assignment : protege contre un caller qui passerait
# `**payload.model_dump()` avec des champs non souhaites (is_active, role, etc.).
_ORG_WRITABLE = frozenset({
    "name", "slug", "contact_email", "plan", "trial_ends_at",
})
_TENANT_WRITABLE = frozenset({
    "organization_id", "name", "slug", "erp_type", "erp_config",
    "cosium_tenant", "cosium_login", "cosium_password_enc",
})
_USER_WRITABLE = frozenset({
    "email", "password_hash", "role", "is_active",
})


def _filter(kwargs: dict, allowed: frozenset) -> dict:
    return {k: v for k, v in kwargs.items() if k in allowed}


def get_user_by_email(db: Session, email: str) -> User | None:
    """Find a user by email."""
    return db.scalars(select(User).where(User.email == email)).first()


def get_tenant_by_slug(db: Session, slug: str) -> Tenant | None:
    """Find a tenant by slug."""
    return db.scalars(select(Tenant).where(Tenant.slug == slug)).first()


def get_org_by_slug(db: Session, slug: str) -> Organization | None:
    """Find an organization by slug."""
    return db.scalars(select(Organization).where(Organization.slug == slug)).first()


def get_tenant_by_id(db: Session, tenant_id: int) -> Tenant | None:
    """Find a tenant by ID."""
    return db.scalars(select(Tenant).where(Tenant.id == tenant_id)).first()


def get_org_by_id(db: Session, org_id: int) -> Organization | None:
    """Find an organization by ID."""
    return db.scalars(select(Organization).where(Organization.id == org_id)).first()


def get_tenant_by_stripe_customer_id(db: Session, customer_id: str) -> Tenant | None:
    """Lookup utilise par les webhooks Stripe (customer.* events)."""
    return db.scalars(
        select(Tenant).where(Tenant.stripe_customer_id == customer_id)
    ).first()


def get_tenant_by_stripe_subscription_id(db: Session, subscription_id: str) -> Tenant | None:
    """Lookup utilise par les webhooks Stripe (subscription.* events)."""
    return db.scalars(
        select(Tenant).where(Tenant.stripe_subscription_id == subscription_id)
    ).first()


def get_active_cosium_tenants(db: Session) -> list[Tenant]:
    """Return all active tenants with Cosium connected."""
    return list(
        db.scalars(
            select(Tenant).where(Tenant.is_active.is_(True), Tenant.cosium_connected.is_(True))
        ).all()
    )


def get_active_tenants(db: Session) -> list[Tenant]:
    """Return all active tenants."""
    return list(
        db.scalars(
            select(Tenant).where(Tenant.is_active.is_(True))
        ).all()
    )


def has_customers(db: Session, tenant_id: int) -> bool:
    """Check if tenant has at least one customer."""
    return db.scalar(
        select(Customer.id).where(Customer.tenant_id == tenant_id).limit(1)
    ) is not None


def create_organization(db: Session, **kwargs) -> Organization:
    """Create and flush an organization (whitelisted fields)."""
    org = Organization(**_filter(kwargs, _ORG_WRITABLE))
    db.add(org)
    db.flush()
    return org


def create_tenant(db: Session, **kwargs) -> Tenant:
    """Create and flush a tenant (whitelisted fields). `require_admin_mfa`
    est volontairement exclu : seul l'endpoint admin dedie peut le toggler.
    """
    tenant = Tenant(**_filter(kwargs, _TENANT_WRITABLE))
    db.add(tenant)
    db.flush()
    return tenant


def create_user(db: Session, **kwargs) -> User:
    """Create and flush a user (whitelisted fields). Exclut `totp_enabled`,
    `totp_secret_enc`, `totp_backup_codes_hash_json` : MFA uniquement via
    son flow dedie.
    """
    user = User(**_filter(kwargs, _USER_WRITABLE))
    db.add(user)
    db.flush()
    return user


def create_tenant_user(db: Session, user_id: int, tenant_id: int, role: str) -> TenantUser:
    """Create a tenant-user mapping."""
    tu = TenantUser(user_id=user_id, tenant_id=tenant_id, role=role)
    db.add(tu)
    return tu
