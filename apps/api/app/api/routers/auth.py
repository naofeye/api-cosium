from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
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
    SessionInfo,
    SwitchTenantRequest,
    TokenResponse,
    UserMeResponse,
)
from app.models import User
from app.repositories import refresh_token_repo
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_COOKIE_OPTS: dict = {
    "httponly": True,
    "samesite": "strict",
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
    # Non-httpOnly flag so frontend can detect auth status (no secret).
    # Reste non-httpOnly (lisible JS) mais secure=True en prod pour eviter fuite sur HTTP.
    response.set_cookie(
        "optiflow_authenticated",
        "true",
        max_age=settings.refresh_token_expire_days * 86400,
        path="/",
        samesite="strict",
        secure=settings.app_env not in ("local", "development", "test"),
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("optiflow_token", **_COOKIE_OPTS)
    response.delete_cookie("optiflow_refresh", **_COOKIE_OPTS)
    response.delete_cookie(
        "optiflow_authenticated",
        path="/",
        samesite="strict",
        secure=settings.app_env not in ("local", "development", "test"),
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Connexion",
    description="Authentifie un utilisateur par email et mot de passe, retourne les cookies JWT.",
)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    result = auth_service.authenticate(db, payload)
    _set_auth_cookies(response, result)
    return LoginResponse(
        role=result.role,
        tenant_id=result.tenant_id,
        tenant_name=result.tenant_name,
        available_tenants=result.available_tenants,
    )


@router.post(
    "/refresh",
    status_code=204,
    summary="Rafraichir le token",
    description="Renouvelle les tokens JWT via le cookie de refresh.",
)
def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    # Read refresh token from httpOnly cookie (not from body)
    refresh_tok = request.cookies.get("optiflow_refresh")
    if not refresh_tok:
        raise AuthenticationError("Refresh token manquant")
    result = auth_service.refresh(db, refresh_tok)
    _set_auth_cookies(response, result)


@router.post(
    "/switch-tenant",
    response_model=LoginResponse,
    summary="Changer de magasin",
    description="Bascule vers un autre tenant accessible par l'utilisateur.",
)
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


@router.post(
    "/change-password",
    status_code=204,
    summary="Changer le mot de passe",
    description="Modifie le mot de passe de l'utilisateur connecte.",
)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    auth_service.change_password(db, current_user.id, payload.old_password, payload.new_password)


@router.post(
    "/forgot-password",
    status_code=204,
    summary="Mot de passe oublie",
    description="Envoie un email de reinitialisation de mot de passe.",
)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)) -> None:
    auth_service.request_password_reset(db, payload.email)


@router.post(
    "/reset-password",
    status_code=204,
    summary="Reinitialiser le mot de passe",
    description="Definit un nouveau mot de passe a partir du token de reinitialisation.",
)
def reset_password_endpoint(payload: ResetPasswordRequest, db: Session = Depends(get_db)) -> None:
    auth_service.reset_password(db, payload.token, payload.new_password)


@router.post(
    "/logout", status_code=204, summary="Deconnexion", description="Revoque le refresh token et supprime les cookies."
)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    # Blacklister l'access token pour empecher sa reutilisation
    access_tok = request.cookies.get("optiflow_token")
    if access_tok:
        from app.security import blacklist_access_token
        blacklist_access_token(access_tok)
    refresh_tok = request.cookies.get("optiflow_refresh")
    if refresh_tok:
        auth_service.logout(db, refresh_tok)
    _clear_auth_cookies(response)


@router.post(
    "/logout-all",
    status_code=204,
    summary="Deconnexion de toutes les sessions",
    description="Revoque tous les refresh tokens de l'utilisateur connecte.",
)
def logout_all(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    refresh_token_repo.revoke_all_for_user(db, current_user.id)
    db.commit()
    _clear_auth_cookies(response)


@router.get(
    "/sessions",
    response_model=list[SessionInfo],
    summary="Lister les sessions actives",
    description="Retourne toutes les sessions actives (refresh tokens non revokes) de l'utilisateur.",
)
def list_sessions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SessionInfo]:
    import hashlib
    current_refresh = request.cookies.get("optiflow_refresh") or ""
    current_hash = hashlib.sha256(current_refresh.encode()).hexdigest() if current_refresh else ""
    sessions = refresh_token_repo.list_active_for_user(db, current_user.id)
    return [
        SessionInfo(
            id=s.id,
            created_at=s.created_at.isoformat(),
            expires_at=s.expires_at.isoformat(),
            is_current=(s.token == current_hash),
        )
        for s in sessions
    ]


@router.post(
    "/sessions/{session_id}/revoke",
    status_code=204,
    summary="Revoquer une session",
    description="Revoque un refresh token specifique (utile pour deconnecter un autre appareil).",
)
def revoke_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    if not refresh_token_repo.revoke_by_id(db, current_user.id, session_id):
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Session", session_id)
    db.commit()


@router.get(
    "/me",
    response_model=UserMeResponse,
    summary="Profil utilisateur",
    description="Retourne les informations de l'utilisateur connecte.",
)
def get_me(current_user: User = Depends(get_current_user)) -> UserMeResponse:
    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
    )


# --- MFA / TOTP ---


class MfaSetupResponse(BaseModel):
    secret: str
    otpauth_uri: str
    issuer: str


class MfaCodePayload(BaseModel):
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class MfaStatusResponse(BaseModel):
    enabled: bool


@router.get(
    "/mfa/status",
    response_model=MfaStatusResponse,
    summary="Etat MFA du compte",
)
def mfa_status(current_user: User = Depends(get_current_user)) -> MfaStatusResponse:
    return MfaStatusResponse(enabled=current_user.totp_enabled)


@router.post(
    "/mfa/setup",
    response_model=MfaSetupResponse,
    summary="Demarrer l'enrolement MFA (TOTP)",
    description=(
        "Genere un secret TOTP et retourne l'URI otpauth:// pour QR code. "
        "N'active pas encore MFA : appeler POST /mfa/enable avec le premier code."
    ),
)
def mfa_setup(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MfaSetupResponse:
    from app.services import mfa_service

    result = mfa_service.start_enrollment(db, current_user)
    return MfaSetupResponse(**result)


@router.post(
    "/mfa/enable",
    status_code=204,
    summary="Activer MFA apres validation premier code",
)
def mfa_enable(
    payload: MfaCodePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    from app.services import mfa_service

    mfa_service.enable_mfa(db, current_user, payload.code)


class MfaDisablePayload(BaseModel):
    password: str = Field(..., min_length=1)


@router.post(
    "/mfa/disable",
    status_code=204,
    summary="Desactiver MFA (necessite mot de passe)",
)
def mfa_disable(
    payload: MfaDisablePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    from app.security import verify_password
    from app.services import mfa_service

    if not verify_password(payload.password, current_user.password_hash):
        from app.core.exceptions import AuthenticationError
        raise AuthenticationError("Mot de passe incorrect")
    mfa_service.disable_mfa(db, current_user, password_verified=True)


# --- MFA Backup codes ---


class MfaBackupCodesResponse(BaseModel):
    codes: list[str]
    remaining: int


class MfaBackupCodesCountResponse(BaseModel):
    remaining: int


@router.post(
    "/mfa/backup-codes/generate",
    response_model=MfaBackupCodesResponse,
    summary="Generer 10 codes de secours MFA",
    description=(
        "Remplace les anciens codes. Les codes ne sont montres QU'UNE SEULE FOIS : "
        "l'utilisateur doit les stocker immediatement (print / password manager). "
        "Chaque code est utilisable une fois en remplacement du code TOTP."
    ),
)
def mfa_backup_codes_generate(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MfaBackupCodesResponse:
    from app.services import mfa_service

    codes = mfa_service.generate_backup_codes(db, current_user)
    return MfaBackupCodesResponse(codes=codes, remaining=len(codes))


@router.get(
    "/mfa/backup-codes/count",
    response_model=MfaBackupCodesCountResponse,
    summary="Nombre de codes de secours restants",
)
def mfa_backup_codes_count(
    current_user: User = Depends(get_current_user),
) -> MfaBackupCodesCountResponse:
    from app.services import mfa_service

    return MfaBackupCodesCountResponse(
        remaining=mfa_service.count_remaining_backup_codes(current_user),
    )
