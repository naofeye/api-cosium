"""Security policy endpoints pour le tenant (MFA enforcement, etc.)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.core.tenant_context import TenantContext
from app.db.session import get_db
from app.models import Tenant
from app.services import audit_service

logger = get_logger("admin_tenant_security")

router = APIRouter(prefix="/api/v1/admin/tenant/security", tags=["admin"])


class TenantSecurityResponse(BaseModel):
    require_admin_mfa: bool

    model_config = ConfigDict(from_attributes=True)


class TenantSecurityUpdate(BaseModel):
    require_admin_mfa: bool


@router.get(
    "",
    response_model=TenantSecurityResponse,
    summary="Lire la politique de securite du tenant",
)
def get_security_policy(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
) -> TenantSecurityResponse:
    tenant = db.get(Tenant, tenant_ctx.tenant_id)
    if not tenant:
        raise NotFoundError("tenant", tenant_ctx.tenant_id)
    return TenantSecurityResponse.model_validate(tenant)


@router.patch(
    "",
    response_model=TenantSecurityResponse,
    summary="Mettre a jour la politique de securite du tenant",
    description=(
        "Active/desactive `require_admin_mfa`. Si active : les users avec role "
        "admin sur ce tenant DOIVENT avoir MFA/TOTP enrole, sinon login refuse "
        "avec MFA_SETUP_REQUIRED. Action auditee."
    ),
)
def update_security_policy(
    payload: TenantSecurityUpdate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
) -> TenantSecurityResponse:
    tenant = db.get(Tenant, tenant_ctx.tenant_id)
    if not tenant:
        raise NotFoundError("tenant", tenant_ctx.tenant_id)

    old_value = {"require_admin_mfa": tenant.require_admin_mfa}
    tenant.require_admin_mfa = payload.require_admin_mfa
    db.commit()
    db.refresh(tenant)

    audit_service.log_action(
        db,
        tenant_ctx.tenant_id,
        tenant_ctx.user_id,
        "update",
        "tenant_security",
        tenant.id,
        old_value=old_value,
        new_value={"require_admin_mfa": payload.require_admin_mfa},
    )
    logger.info(
        "tenant_security_policy_updated",
        tenant_id=tenant.id,
        user_id=tenant_ctx.user_id,
        require_admin_mfa=payload.require_admin_mfa,
    )
    return TenantSecurityResponse.model_validate(tenant)
