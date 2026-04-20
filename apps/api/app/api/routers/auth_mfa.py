"""MFA / TOTP routes for authentication.

Extracted from auth.py to keep files under 300 lines.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


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
