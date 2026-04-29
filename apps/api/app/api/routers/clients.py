from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session

from app.core.constants import ROLE_ADMIN
from app.core.deps import require_permission, require_tenant_role
from app.core.exceptions import BusinessError, ValidationError
from app.core.http import content_disposition
from app.core.redis_cache import acquire_lock, release_lock
from app.core.tenant_context import TenantContext, get_tenant_context
from app.core.upload_safe import read_upload_safely
from app.db.session import get_db
from app.domain.schemas.clients import (
    ClientCreate,
    ClientImportResult,
    ClientListResponse,
    ClientMergeRequest,
    ClientMergeResult,
    ClientResponse,
    ClientUpdate,
    DuplicateGroup,
)
from app.services import client_service

router = APIRouter(prefix="/api/v1/clients", tags=["clients"])


@router.get(
    "",
    response_model=ClientListResponse,
    summary="Lister les clients",
    description="Retourne la liste paginee des clients du magasin avec recherche optionnelle.",
)
def list_clients(
    query: str = Query("", alias="q", max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ClientListResponse:
    effective_include_deleted = include_deleted and tenant_ctx.role == ROLE_ADMIN
    return client_service.search_clients(
        db,
        tenant_id=tenant_ctx.tenant_id,
        query=query,
        page=page,
        page_size=page_size,
        include_deleted=effective_include_deleted,
    )


@router.get(
    "/duplicates",
    response_model=list[DuplicateGroup],
    summary="Detecter les doublons",
    description="Retourne les groupes de clients potentiellement en doublon.",
)
def get_duplicates(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[DuplicateGroup]:
    return client_service.find_duplicates(db, tenant_id=tenant_ctx.tenant_id)


@router.get(
    "/import/template",
    summary="Telecharger le modele d'import",
    description="Telecharge un fichier CSV modele pour l'import de clients.",
)
def download_import_template() -> Response:
    data = client_service.generate_import_template()
    return Response(
        content=data,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": content_disposition("modele_import_clients.csv")},
    )


@router.post(
    "/merge",
    response_model=ClientMergeResult,
    summary="Fusionner deux clients",
    description="Fusionne le client merge_id dans keep_id. Transfere les dossiers, interactions, PEC, etc.",
)
def merge_clients(
    payload: ClientMergeRequest,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> ClientMergeResult:
    lock_key = f"merge:client:{tenant_ctx.tenant_id}:{payload.keep_id}:{payload.merge_id}"
    if not acquire_lock(lock_key, ttl=60):
        raise BusinessError("Une fusion est deja en cours pour ces clients")
    try:
        return client_service.merge_clients(
            db,
            tenant_id=tenant_ctx.tenant_id,
            keep_id=payload.keep_id,
            merge_id=payload.merge_id,
            user_id=tenant_ctx.user_id,
        )
    finally:
        release_lock(lock_key)


@router.post(
    "/import",
    response_model=ClientImportResult,
    summary="Importer des clients depuis un fichier",
    description="Importe des clients en lot depuis un fichier CSV ou Excel (.xlsx).",
)
async def import_file(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_permission("create", "client")),
) -> ClientImportResult:
    allowed_extensions = (".csv", ".xlsx", ".xls")
    if not file.filename or not file.filename.lower().endswith(allowed_extensions):
        raise ValidationError("file", "Le fichier doit etre au format CSV ou Excel (.xlsx).")
    content = await read_upload_safely(file, request)
    return client_service.import_from_file(
        db,
        tenant_id=tenant_ctx.tenant_id,
        file_content=content,
        filename=file.filename,
        user_id=tenant_ctx.user_id,
    )


@router.get(
    "/{client_id}/quick",
    summary="Apercu rapide d'un client",
    description="Retourne un apercu leger du client (pour hover card).",
)
def get_client_quick(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    return client_service.get_client_quick(db, tenant_id=tenant_ctx.tenant_id, client_id=client_id)


@router.get(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Detail d'un client",
    description="Retourne les informations detaillees d'un client.",
)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ClientResponse:
    return client_service.get_client(db, tenant_id=tenant_ctx.tenant_id, client_id=client_id)


@router.post(
    "",
    response_model=ClientResponse,
    status_code=201,
    summary="Creer un client",
    description="Cree un nouveau client dans le magasin.",
)
def create_client(
    payload: ClientCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_permission("create", "client")),
) -> ClientResponse:
    return client_service.create_client(db, tenant_id=tenant_ctx.tenant_id, payload=payload, user_id=tenant_ctx.user_id)


@router.put(
    "/{client_id}",
    response_model=ClientResponse,
    summary="Modifier un client",
    description="Met a jour les informations d'un client existant.",
)
def update_client(
    client_id: int,
    payload: ClientUpdate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_permission("edit", "client")),
) -> ClientResponse:
    return client_service.update_client(
        db,
        tenant_id=tenant_ctx.tenant_id,
        client_id=client_id,
        payload=payload,
        user_id=tenant_ctx.user_id,
    )


@router.delete(
    "/{client_id}",
    status_code=200,
    summary="Supprimer un client",
    description="Supprime un client (soft delete).",
)
def delete_client(
    client_id: int,
    force: bool = False,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> dict[str, str]:
    if force and tenant_ctx.role != ROLE_ADMIN:
        raise BusinessError(
            "FORCE_DELETE_ADMIN_ONLY",
            "La suppression forcee est reservee aux administrateurs.",
        )
    client_service.delete_client(db, tenant_id=tenant_ctx.tenant_id, client_id=client_id, user_id=tenant_ctx.user_id, force=force)
    return {"message": "Client supprime avec succes"}


@router.post(
    "/{client_id}/restore",
    response_model=ClientResponse,
    summary="Restaurer un client",
    description="Restaure un client precedemment supprime.",
)
def restore_client(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin")),
) -> ClientResponse:
    return client_service.restore_client(
        db, tenant_id=tenant_ctx.tenant_id, client_id=client_id, user_id=tenant_ctx.user_id
    )


@router.post(
    "/{client_id}/avatar",
    summary="Telecharger un avatar",
    description="Upload une photo de profil pour un client.",
)
async def upload_avatar(
    client_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_permission("edit", "client")),
) -> dict[str, str]:
    allowed = {"image/jpeg", "image/png", "image/jpg"}
    if file.content_type not in allowed:
        raise ValidationError("file", "Le fichier doit etre une image (JPG ou PNG).")
    # Avatar : limite stricte 5 MB (vs default settings.max_upload_size_mb=20).
    file_data = await read_upload_safely(file, request, max_mb=5)
    url = client_service.upload_avatar(
        db,
        tenant_id=tenant_ctx.tenant_id,
        client_id=client_id,
        file_data=file_data,
        content_type=file.content_type or "image/jpeg",
        user_id=tenant_ctx.user_id,
    )
    return {"avatar_url": url}


@router.get(
    "/{client_id}/avatar",
    summary="Obtenir l'avatar",
    description="Redirige vers l'URL de l'avatar du client.",
)
def get_avatar(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> RedirectResponse:
    url = client_service.get_avatar_url(db, tenant_id=tenant_ctx.tenant_id, client_id=client_id)
    return RedirectResponse(url=url)
