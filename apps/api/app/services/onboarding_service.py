import re
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
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
from app.repositories import onboarding_repo, refresh_token_repo
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
    while onboarding_repo.get_tenant_by_slug(db, slug) is not None:
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def signup(db: Session, payload: SignupRequest) -> TokenResponse:
    existing = onboarding_repo.get_user_by_email(db, payload.owner_email)
    if existing:
        raise ValidationError("owner_email", "Un compte existe déjà avec cet email")

    org_slug = _slugify(payload.company_name)
    org_counter = 1
    final_org_slug = org_slug
    while onboarding_repo.get_org_by_slug(db, final_org_slug):
        final_org_slug = f"{org_slug}-{org_counter}"
        org_counter += 1

    org = onboarding_repo.create_organization(
        db,
        name=payload.company_name,
        slug=final_org_slug,
        contact_email=payload.owner_email,
        plan="trial",
        trial_ends_at=datetime.now(UTC) + timedelta(days=TRIAL_DAYS),
    )

    tenant = None
    max_slug_attempts = 3
    for attempt in range(max_slug_attempts):
        tenant_slug = _ensure_unique_slug(db, org_slug)
        try:
            tenant = onboarding_repo.create_tenant(
                db,
                organization_id=org.id,
                name=payload.company_name,
                slug=tenant_slug,
            )
            db.flush()
            break
        except IntegrityError:
            db.rollback()
            # Re-create org since rollback discarded it
            org = onboarding_repo.create_organization(
                db,
                name=payload.company_name,
                slug=final_org_slug,
                contact_email=payload.owner_email,
                plan="trial",
                trial_ends_at=datetime.now(UTC) + timedelta(days=TRIAL_DAYS),
            )
            if attempt == max_slug_attempts - 1:
                raise BusinessError("Impossible de créer le magasin, veuillez réessayer.")

    user = onboarding_repo.create_user(
        db,
        email=payload.owner_email,
        password_hash=hash_password(payload.owner_password),
        role="admin",
        is_active=True,
    )

    onboarding_repo.create_tenant_user(db, user.id, tenant.id, "admin")
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
    tenant = onboarding_repo.get_tenant_by_id(db, tenant_id)
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
    except (ConnectionError, TimeoutError, OSError, ValueError) as e:
        logger.warning("erp_connection_failed", tenant_id=tenant_id, error=str(e))
        raise BusinessError("Connexion ERP echouee. Verifiez vos identifiants et reessayez.") from e

    tenant.cosium_tenant = payload.cosium_tenant
    tenant.cosium_login = payload.cosium_login
    tenant.cosium_password_enc = encrypt(payload.cosium_password)
    tenant.cosium_connected = True
    db.commit()

    logger.info("erp_connected", tenant_id=tenant_id, erp_type=tenant.erp_type, cosium_tenant=payload.cosium_tenant)
    return True


def trigger_first_sync(db: Session, tenant_id: int) -> dict:
    tenant = onboarding_repo.get_tenant_by_id(db, tenant_id)
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
    except (ConnectionError, TimeoutError, OSError, ValueError) as e:
        logger.error("first_sync_failed", tenant_id=tenant_id, error=str(e))
        raise BusinessError("Synchronisation echouee. Verifiez la connexion ERP et reessayez.") from e


def update_cosium_cookies(db: Session, tenant_id: int, access_token: str, device_credential: str) -> bool:
    """Store encrypted Cosium browser cookies for the tenant."""
    tenant = onboarding_repo.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise BusinessError("Magasin introuvable")

    tenant.cosium_cookie_access_token_enc = encrypt(access_token)
    tenant.cosium_cookie_device_credential_enc = encrypt(device_credential)
    tenant.cosium_connected = True
    db.commit()

    logger.info("cosium_cookies_updated", tenant_id=tenant_id)
    return True


def get_onboarding_status(db: Session, tenant_id: int) -> OnboardingStatusResponse:
    tenant = onboarding_repo.get_tenant_by_id(db, tenant_id)
    if not tenant:
        raise BusinessError("Magasin introuvable")

    org = onboarding_repo.get_org_by_id(db, tenant.organization_id)

    has_customers = onboarding_repo.has_customers(db, tenant_id)

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
