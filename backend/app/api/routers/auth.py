from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.exceptions import AuthenticationError
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LoginResponse,
    ResetPasswordRequest,
    SwitchTenantRequest,
    TokenResponse,
    UserMeResponse,
)
from app.models import User
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_COOKIE_OPTS: dict = {
    "httponly": True,
    "samesite": "lax",
    "secure": settings.app_env not in ("local", "development", "test"),
    "path": "/",
}


def _set_auth_cookies(response: Response, result: TokenResponse) -> None:
    response.set_cookie(
        "optiflow_token", result.access_token, max_age=settings.access_token_expire_minutes * 60, **_COOKIE_OPTS
    )
    response.set_cookie(
        "optiflow_refresh", result.refresh_token, max_age=settings.refresh_token_expire_days * 86400, **_COOKIE_OPTS
    )
    # Non-httpOnly flag so middleware/frontend can detect auth status (no secret)
    response.set_cookie(
        "optiflow_authenticated", "true", max_age=settings.refresh_token_expire_days * 86400, path="/", samesite="lax"
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    result = auth_service.authenticate(db, payload)
    _set_auth_cookies(response, result)
    return LoginResponse(
        role=result.role,
        tenant_id=result.tenant_id,
        tenant_name=result.tenant_name,
        available_tenants=result.available_tenants,
    )


@router.post("/refresh", status_code=204)
def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    # Read refresh token from httpOnly cookie (not from body)
    refresh_tok = request.cookies.get("optiflow_refresh")
    if not refresh_tok:
        raise AuthenticationError("Refresh token manquant")
    result = auth_service.refresh(db, refresh_tok)
    _set_auth_cookies(response, result)


@router.post("/switch-tenant", response_model=LoginResponse)
def switch_tenant(
    payload: SwitchTenantRequest,
    response: Response,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> LoginResponse:
    result = auth_service.switch_tenant(db, tenant_ctx.user_id, payload.tenant_id)
    _set_auth_cookies(response, result)
    return LoginResponse(
        role=result.role,
        tenant_id=result.tenant_id,
        tenant_name=result.tenant_name,
        available_tenants=result.available_tenants,
    )


@router.post("/change-password", status_code=204)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    auth_service.change_password(db, current_user.id, payload.old_password, payload.new_password)


@router.post("/forgot-password", status_code=204)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> None:
    auth_service.request_password_reset(db, payload.email)


@router.post("/reset-password", status_code=204)
def reset_password_endpoint(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> None:
    auth_service.reset_password(db, payload.token, payload.new_password)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    refresh_tok = request.cookies.get("optiflow_refresh")
    if refresh_tok:
        auth_service.logout(db, refresh_tok)
    response.delete_cookie("optiflow_token", path="/")
    response.delete_cookie("optiflow_refresh", path="/")
    response.delete_cookie("optiflow_authenticated", path="/")


@router.get("/me", response_model=UserMeResponse)
def get_me(current_user: User = Depends(get_current_user)) -> UserMeResponse:
    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
    )
