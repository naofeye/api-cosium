"""Repository for onboarding operations."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer, Organization, Tenant, TenantUser, User


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


def has_customers(db: Session, tenant_id: int) -> bool:
    """Check if tenant has at least one customer."""
    return db.scalar(
        select(Customer.id).where(Customer.tenant_id == tenant_id).limit(1)
    ) is not None


def create_organization(db: Session, **kwargs) -> Organization:
    """Create and flush an organization."""
    org = Organization(**kwargs)
    db.add(org)
    db.flush()
    return org


def create_tenant(db: Session, **kwargs) -> Tenant:
    """Create and flush a tenant."""
    tenant = Tenant(**kwargs)
    db.add(tenant)
    db.flush()
    return tenant


def create_user(db: Session, **kwargs) -> User:
    """Create and flush a user."""
    user = User(**kwargs)
    db.add(user)
    db.flush()
    return user


def create_tenant_user(db: Session, user_id: int, tenant_id: int, role: str) -> TenantUser:
    """Create a tenant-user mapping."""
    tu = TenantUser(user_id=user_id, tenant_id=tenant_id, role=role)
    db.add(tu)
    return tu
