"""Router for client-mutuelle associations."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_permission, require_tenant_role
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.client_mutuelle import (
    ClientMutuelleCreate,
    ClientMutuelleResponse,
    MutuelleDetectionResult,
)
from app.services import client_mutuelle_service

router = APIRouter(prefix="/api/v1", tags=["client-mutuelles"])


@router.get(
    "/clients/{client_id}/mutuelles",
    response_model=list[ClientMutuelleResponse],
    summary="Lister les mutuelles d'un client",
    description="Retourne toutes les mutuelles detectees ou saisies pour un client.",
)
def list_client_mutuelles(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[ClientMutuelleResponse]:
    return client_mutuelle_service.get_client_mutuelles(
        db, tenant_ctx.tenant_id, client_id
    )


@router.post(
    "/clients/{client_id}/mutuelles",
    response_model=ClientMutuelleResponse,
    status_code=201,
    summary="Ajouter une mutuelle a un client",
    description="Ajoute manuellement une mutuelle a un client.",
    dependencies=[Depends(require_permission("create", "client_mutuelle"))],
)
def add_client_mutuelle(
    client_id: int,
    payload: ClientMutuelleCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ClientMutuelleResponse:
    return client_mutuelle_service.add_client_mutuelle(
        db, tenant_ctx.tenant_id, client_id, payload
    )


@router.delete(
    "/clients/{client_id}/mutuelles/{mutuelle_id}",
    status_code=204,
    summary="Supprimer une mutuelle d'un client",
    description="Supprime une association client-mutuelle.",
    dependencies=[Depends(require_permission("delete", "client_mutuelle"))],
)
def delete_client_mutuelle(
    client_id: int,
    mutuelle_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> None:
    client_mutuelle_service.delete_client_mutuelle(
        db, tenant_ctx.tenant_id, client_id, mutuelle_id
    )


@router.post(
    "/admin/detect-mutuelles",
    response_model=MutuelleDetectionResult,
    summary="Detection batch des mutuelles",
    description="Detecte automatiquement les mutuelles de tous les clients a partir des donnees Cosium.",
    dependencies=[Depends(require_tenant_role("admin"))],
)
def batch_detect_mutuelles(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> MutuelleDetectionResult:
    return client_mutuelle_service.detect_all_clients_mutuelles(
        db, tenant_ctx.tenant_id
    )
