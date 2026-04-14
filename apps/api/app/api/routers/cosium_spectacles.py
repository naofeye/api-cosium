"""Routes de lecture des dossiers lunettes Cosium — LECTURE SEULE.

Expose au frontend les donnees optiques (metadata, dioptries, selection) pour
un dossier Cosium donne. Pas d'ecriture vers Cosium (seule POST auth autorise).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.spectacle import SpectacleFileComplete, SpectacleFileMeta
from app.integrations.cosium.cosium_connector import CosiumConnector
from app.services import spectacle_service
from app.services.erp_auth_service import _authenticate_connector, _get_connector_for_tenant

router = APIRouter(prefix="/api/v1/cosium/spectacles", tags=["cosium-spectacles"])


def _get_cosium_connector(db: Session, tenant_id: int) -> CosiumConnector:
    """Retourne un CosiumConnector authentifie pour le tenant courant."""
    connector, tenant = _get_connector_for_tenant(db, tenant_id)
    if not isinstance(connector, CosiumConnector):
        from app.core.exceptions import BusinessError
        raise BusinessError("Le tenant n'utilise pas Cosium comme ERP")
    _authenticate_connector(connector, tenant)
    return connector


@router.get(
    "/customer/{customer_cosium_id}",
    response_model=list[SpectacleFileMeta],
    summary="Liste les dossiers lunettes d'un client",
    description="Recupere la liste des dossiers lunettes Cosium d'un client (metadata seulement).",
)
def list_for_customer(
    customer_cosium_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[SpectacleFileMeta]:
    connector = _get_cosium_connector(db, tenant_ctx.tenant_id)
    items = spectacle_service.list_spectacle_files_for_customer(connector, customer_cosium_id)
    return [SpectacleFileMeta(**i) for i in items]


@router.get(
    "/{file_id}",
    response_model=SpectacleFileComplete,
    summary="Dossier lunettes complet",
    description="Recupere un dossier lunettes Cosium : metadata, dioptries et selection courante.",
)
def get_complete(
    file_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> SpectacleFileComplete:
    connector = _get_cosium_connector(db, tenant_ctx.tenant_id)
    data = spectacle_service.get_spectacle_file_complete(connector, file_id)
    return SpectacleFileComplete(**data)
