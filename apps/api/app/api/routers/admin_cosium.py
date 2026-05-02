"""Admin Cosium connection test and cookie management endpoints."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import require_tenant_role
from app.core.tenant_context import TenantContext
from app.db.session import get_db
from app.repositories import onboarding_repo
from app.services import onboarding_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _check_cosium_status(db: Session, tenant_id: int | None = None) -> dict:
    """Quick Cosium connectivity check using tenant-scoped credentials.

    If tenant_id is provided, uses tenant-stored cookies/credentials.
    Otherwise falls back to global settings.
    """
    try:
        from app.core.encryption import decrypt
        from app.integrations.cosium.client import CosiumClient

        client = CosiumClient()
        client.base_url = settings.cosium_base_url

        if tenant_id is not None:
            tenant = onboarding_repo.get_tenant_by_id(db, tenant_id)
            if not tenant:
                return {"status": "error", "error": "tenant introuvable"}

            client.tenant = tenant.cosium_tenant or settings.cosium_tenant or ""

            # Try tenant-stored cookies first
            tenant_at = getattr(tenant, "cosium_cookie_access_token_enc", None)
            tenant_dc = getattr(tenant, "cosium_cookie_device_credential_enc", None)
            if tenant_at and tenant_dc:
                at_plain = decrypt(tenant_at)
                dc_plain = decrypt(tenant_dc)
                client._authenticate_cookie(access_token=at_plain, device_credential=dc_plain)
                return {"status": "ok"}

        # Fallback to global settings
        client.authenticate()
        return {"status": "ok"}
    except Exception as exc:
        msg = str(exc)
        if "401" in msg:
            return {"status": "degraded", "error": "cookie expired"}
        return {"status": "error", "error": "unavailable"}


class CosiumConnectionTest(BaseModel):
    connected: bool
    error: str | None = None
    tenant: str = ""
    customers_total: int | None = None


@router.get(
    "/cosium-test",
    response_model=CosiumConnectionTest,
    summary="Tester la connexion Cosium",
    description="Verifie si les cookies Cosium sont valides en faisant un appel API test.",
)
def test_cosium_connection(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> CosiumConnectionTest:
    """Test Cosium connection using tenant-scoped credentials."""
    try:
        from app.core.encryption import decrypt
        from app.integrations.cosium.client import CosiumClient

        tenant = onboarding_repo.get_tenant_by_id(db, tenant_ctx.tenant_id)
        client = CosiumClient()
        client.base_url = settings.cosium_base_url

        if tenant:
            client.tenant = tenant.cosium_tenant or settings.cosium_tenant or ""
            tenant_at = getattr(tenant, "cosium_cookie_access_token_enc", None)
            tenant_dc = getattr(tenant, "cosium_cookie_device_credential_enc", None)
            tenant_login = getattr(tenant, "cosium_login", None)
            tenant_pwd_enc = getattr(tenant, "cosium_password_enc", None)
            if tenant_at and tenant_dc:
                at_plain = decrypt(tenant_at)
                dc_plain = decrypt(tenant_dc)
                client._authenticate_cookie(access_token=at_plain, device_credential=dc_plain)
            elif tenant_login and tenant_pwd_enc:
                # Priorite credentials tenant > settings globaux : eviter de
                # declarer un tenant en echec quand sa config Basic dediee
                # est correcte mais sans cookies.
                pwd_plain = decrypt(tenant_pwd_enc)
                client.authenticate(
                    tenant=client.tenant,
                    login=tenant_login,
                    password=pwd_plain,
                )
            else:
                client.authenticate()
        else:
            client.authenticate()

        data = client.get("/customers", {"page_size": 1, "page_number": 0})
        total = data.get("page", {}).get("totalElements") or data.get("totalElements", 0)
        return CosiumConnectionTest(
            connected=True, tenant=client.tenant or "", customers_total=total
        )
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg:
            return CosiumConnectionTest(
                connected=False,
                error="Cookie expire. Veuillez vous reconnecter a Cosium et copier le nouveau cookie access_token.",
            )
        return CosiumConnectionTest(
            connected=False,
            error="Erreur de connexion Cosium. Verifiez vos identifiants et la disponibilite du service.",
        )


class CosiumCookiesPayload(BaseModel):
    access_token: str = Field(
        ..., min_length=1, description="Cookie access_token depuis le navigateur Cosium"
    )
    device_credential: str = Field(
        ..., min_length=1, description="Cookie device-credential depuis le navigateur Cosium"
    )


class CosiumCookiesResponse(BaseModel):
    status: str
    message: str


@router.post(
    "/cosium-cookies",
    response_model=CosiumCookiesResponse,
    summary="Mettre a jour les cookies Cosium",
    description="Enregistre les cookies access_token et device-credential du navigateur Cosium (chiffres en base).",
)
def update_cosium_cookies(
    payload: CosiumCookiesPayload,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
) -> CosiumCookiesResponse:
    """Admin-only: store encrypted Cosium browser cookies for the tenant."""
    onboarding_service.update_cosium_cookies(
        db,
        tenant_id=tenant_ctx.tenant_id,
        access_token=payload.access_token,
        device_credential=payload.device_credential,
    )
    return CosiumCookiesResponse(status="ok", message="Cookies Cosium mis a jour avec succes")



# ---------------------------------------------------------------------------
# Reconciliation factures orphelines (PEC V12)
# ---------------------------------------------------------------------------


class OrphanInvoiceStats(BaseModel):
    total_invoices: int
    orphans: int
    linked_pct: float


class OrphanReconcileResult(BaseModel):
    processed: int
    matched: int
    still_orphan: int


@router.get(
    "/cosium/orphan-invoices",
    response_model=OrphanInvoiceStats,
    summary="Statistiques factures Cosium orphelines",
)
def get_orphan_invoice_stats(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> OrphanInvoiceStats:
    from app.services.orphan_invoice_service import count_orphan_invoices

    stats = count_orphan_invoices(db, tenant_ctx.tenant_id)
    return OrphanInvoiceStats(**stats)


@router.post(
    "/cosium/reconcile-orphans",
    response_model=OrphanReconcileResult,
    summary="Rejoue le matching pour les factures orphelines",
)
def reconcile_orphans(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> OrphanReconcileResult:
    from app.services.orphan_invoice_service import reconcile_orphan_invoices

    # Limite de securite : 5000 factures max par appel synchrone (UI).
    # Pour des volumes plus gros, la task Celery quotidienne tourne deja.
    result = reconcile_orphan_invoices(db, tenant_ctx.tenant_id, limit=5000)
    return OrphanReconcileResult(**result)
