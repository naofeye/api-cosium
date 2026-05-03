from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.auth_cookies import clear_auth_cookies as _clear_auth_cookies
from app.core.auth_cookies import set_auth_cookies as _set_auth_cookies
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
    UserMeResponse,
)
from app.models import User
from app.repositories import refresh_token_repo
from app.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/revoke-all-tokens",
    summary="Revoque tous les tokens de l'utilisateur (logout-everywhere)",
    description="Increment user.token_version. Tous les JWT existants deviennent invalides au prochain refresh. L'utilisateur courant doit se reconnecter sur tous ses appareils.",
)
def revoke_all_tokens(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    current_user.token_version = (current_user.token_version or 0) + 1
    db.commit()
    # Revoke aussi tous les refresh tokens en BDD pour invalider la chaine
    refresh_token_repo.revoke_all_for_user(db, current_user.id)
    _clear_auth_cookies(response)
    return {"status": "revoked", "token_version": current_user.token_version}


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
    "/login-form",
    summary="Connexion via formulaire HTML (no-JS fallback)",
    description=(
        "Endpoint compatible avec un POST application/x-www-form-urlencoded "
        "depuis un <form> HTML natif. Sur succes : 303 redirect vers /actions "
        "avec les cookies JWT poses. Sur echec : 303 redirect vers /login?error=..."
        " Permet de se connecter meme si JavaScript est desactive ou casse."
    ),
)
def login_form(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
    totp_code: str | None = Form(None),
):
    # Defense CSRF / login-CSRF : refuser les soumissions cross-origin.
    # SameSite=strict protege deja les cookies, mais on ajoute une verification
    # explicite Origin/Referer pour empecher un site externe de creer un compte
    # de session fixation via <form action=...>.
    from urllib.parse import quote, urlsplit

    from app.core.config import settings as _settings

    def _normalize_origin(value: str) -> str | None:
        # Reconstruit scheme://host[:port] depuis une URL ou un origin brut.
        if not value:
            return None
        parts = urlsplit(value)
        if not parts.scheme or not parts.netloc:
            return None
        return f"{parts.scheme}://{parts.netloc}".lower()

    allowed_origins = {
        norm
        for raw in _settings.cors_origins.split(",")
        if (norm := _normalize_origin(raw.strip()))
    }
    origin_header = request.headers.get("origin") or request.headers.get("referer", "")
    if origin_header:
        # Comparaison stricte sur scheme://host[:port], pas un prefixe :
        # un origin comme "https://app.example.com.evil.test" ne doit pas matcher
        # "https://app.example.com".
        normalized = _normalize_origin(origin_header)
        if normalized is None or normalized not in allowed_origins:
            return RedirectResponse(
                url=f"/login?error={quote('Origine non autorisee')}",
                status_code=303,
            )

    try:
        payload = LoginRequest(email=email, password=password, totp_code=totp_code or None)
        result = auth_service.authenticate(db, payload)
    except AuthenticationError as exc:
        msg = str(exc) or "Email ou mot de passe incorrect"
        return RedirectResponse(url=f"/login?error={quote(msg)}", status_code=303)
    except Exception:
        return RedirectResponse(url="/login?error=Erreur+inattendue", status_code=303)

    redirect = RedirectResponse(url="/actions", status_code=303)
    _set_auth_cookies(redirect, result)
    return redirect


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
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    # 1. Increment token_version : invalide TOUS les access tokens de cet
    #    utilisateur, pas seulement celui de ce navigateur. Sans ca les
    #    tokens emis sur d'autres devices restaient valides jusqu'a leur
    #    expiration (Codex M6, REVIEW.md 2026-05-03).
    current_user.token_version = (current_user.token_version or 0) + 1
    # 2. Blacklister explicitement l'access token courant : evite une
    #    fenetre de course entre la lecture du JWT et la lecture de
    #    `users.token_version` en BDD.
    access_tok = request.cookies.get("optiflow_token")
    if access_tok:
        from app.security import blacklist_access_token
        blacklist_access_token(access_tok)
    # 3. Revoquer tous les refresh tokens : force re-login sur chaque device.
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
