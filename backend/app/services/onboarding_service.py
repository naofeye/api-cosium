import re
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.encryption import encrypt
from app.core.exceptions import BusinessError, ValidationError
from app.core.logging import get_logger
from app.domain.schemas.auth import TokenResponse
from app.domain.schemas.onboarding import (
    ConnectCosiumRequest,
    OnboardingStatusResponse,
    OnboardingStep,
    SignupRequest,
)
from app.models import Customer, Organization, Tenant, TenantUser, User
from app.repositories import refresh_token_repo
from app.security import (
    create_access_token,
    generate_refresh_token,
    get_refresh_token_expiry,
    hash_password,
)

logger = get_logger("onboarding_service")

TRIAL_DAYS = 14


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:80] or "magasin"


def _ensure_unique_slug(db: Session, base_slug: str) -> str:
    slug = base_slug
    counter = 1
    while db.query(Tenant).filter(Tenant.slug == slug).first() is not None:
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def signup(db: Session, payload: SignupRequest) -> TokenResponse:
    existing = db.query(User).filter(User.email == payload.owner_email).first()
    if existing:
        raise ValidationError("owner_email", "Un compte existe déjà avec cet email")

    org_slug = _slugify(payload.company_name)
    org_counter = 1
    final_org_slug = org_slug
    while db.query(Organization).filter(Organization.slug == final_org_slug).first():
        final_org_slug = f"{org_slug}-{org_counter}"
        org_counter += 1

    org = Organization(
        name=payload.company_name,
        slug=final_org_slug,
        contact_email=payload.owner_email,
        plan="trial",
        trial_ends_at=datetime.now(UTC) + timedelta(days=TRIAL_DAYS),
    )
    db.add(org)
    db.flush()

    tenant_slug = _ensure_unique_slug(db, org_slug)
    tenant = Tenant(
        organization_id=org.id,
        name=payload.company_name,
        slug=tenant_slug,
    )
    db.add(tenant)
    db.flush()

    user = User(
        email=payload.owner_email,
        password_hash=hash_password(payload.owner_password),
        role="admin",
        is_active=True,
    )
    db.add(user)
    db.flush()

    db.add(TenantUser(user_id=user.id, tenant_id=tenant.id, role="admin"))
    db.commit()

    access_token = create_access_token(
        user.email,
        user.role,
        tenant_id=tenant.id,
        is_group_admin=False,
    )
    refresh_token = generate_refresh_token()
    refresh_token_repo.create(db, refresh_token, user.id, get_refresh_token_expiry())

    logger.info("onboarding_signup", org_id=org.id, tenant_id=tenant.id, user_id=user.id)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role,
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        available_tenants=[{"id": tenant.id, "name": tenant.name, "slug": tenant.slug, "role": "admin"}],
    )


def connect_cosium(db: Session, tenant_id: int, payload: ConnectCosiumRequest) -> bool:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise BusinessError("Magasin introuvable")

    from app.core.config import settings
    from app.integrations.erp_factory import get_connector

    connector = get_connector(tenant.erp_type or "cosium")
    try:
        connector.authenticate(
            base_url=settings.cosium_base_url,
            tenant=payload.cosium_tenant,
            login=payload.cosium_login,
            password=payload.cosium_password,
        )
    except Exception as e:
        logger.warning("erp_connection_failed", tenant_id=tenant_id, error=str(e))
        raise BusinessError(f"Connexion ERP echouee : {e}") from e

    tenant.cosium_tenant = payload.cosium_tenant
    tenant.cosium_login = payload.cosium_login
    tenant.cosium_password_enc = encrypt(payload.cosium_password)
    tenant.cosium_connected = True
    db.commit()

    logger.info("erp_connected", tenant_id=tenant_id, erp_type=tenant.erp_type, cosium_tenant=payload.cosium_tenant)
    return True


def trigger_first_sync(db: Session, tenant_id: int) -> dict:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise BusinessError("Magasin introuvable")
    if not tenant.cosium_connected:
        raise BusinessError("Connectez d'abord votre ERP avant de lancer la synchronisation")

    from app.services import erp_sync_service

    try:
        result = erp_sync_service.sync_customers(db, tenant_id=tenant_id)
        tenant.first_sync_done = True
        db.commit()
        logger.info("first_sync_completed", tenant_id=tenant_id)
        return result
    except Exception as e:
        logger.error("first_sync_failed", tenant_id=tenant_id, error=str(e))
        raise BusinessError(f"Synchronisation echouee : {e}") from e


def get_onboarding_status(db: Session, tenant_id: int) -> OnboardingStatusResponse:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise BusinessError("Magasin introuvable")

    org = db.query(Organization).filter(Organization.id == tenant.organization_id).first()

    has_customers = db.query(Customer).filter(Customer.tenant_id == tenant_id).count() > 0

    steps = [
        OnboardingStep(key="account", label="Créer votre compte", completed=True),
        OnboardingStep(key="cosium", label="Connecter votre Cosium", completed=tenant.cosium_connected),
        OnboardingStep(key="sync", label="Importer vos données", completed=tenant.first_sync_done),
        OnboardingStep(key="configure", label="Configurer vos préférences", completed=tenant.first_sync_done),
        OnboardingStep(key="ready", label="C'est prêt !", completed=has_customers and tenant.first_sync_done),
    ]

    current_step = "ready"
    for step in steps:
        if not step.completed:
            current_step = step.key
            break

    trial_days = None
    if org and org.trial_ends_at:
        ends_at = org.trial_ends_at
        if ends_at.tzinfo is None:
            ends_at = ends_at.replace(tzinfo=UTC)
        remaining = (ends_at - datetime.now(UTC)).days
        trial_days = max(0, remaining)

    return OnboardingStatusResponse(
        steps=steps,
        current_step=current_step,
        cosium_connected=tenant.cosium_connected,
        first_sync_done=tenant.first_sync_done,
        trial_days_remaining=trial_days,
    )
