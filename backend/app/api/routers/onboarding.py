from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.auth import TokenResponse
from app.domain.schemas.onboarding import (
    ConnectCosiumRequest,
    ConnectCosiumResult,
    FirstSyncResult,
    OnboardingStatusResponse,
    SignupRequest,
)
from app.services import onboarding_service

router = APIRouter(prefix="/api/v1/onboarding", tags=["onboarding"])


@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(
    payload: SignupRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    return onboarding_service.signup(db, payload=payload)


@router.post("/connect-cosium", response_model=ConnectCosiumResult)
def connect_cosium(
    payload: ConnectCosiumRequest,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ConnectCosiumResult:
    onboarding_service.connect_cosium(db, tenant_id=tenant_ctx.tenant_id, payload=payload)
    return ConnectCosiumResult(status="connected")


@router.post("/first-sync", response_model=FirstSyncResult)
def first_sync(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> FirstSyncResult:
    result = onboarding_service.trigger_first_sync(db, tenant_id=tenant_ctx.tenant_id)
    return FirstSyncResult(status="completed", details=result)


@router.get("/status", response_model=OnboardingStatusResponse)
def get_status(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> OnboardingStatusResponse:
    return onboarding_service.get_onboarding_status(db, tenant_id=tenant_ctx.tenant_id)
