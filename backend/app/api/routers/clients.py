from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.deps import require_tenant_role
from app.core.exceptions import ValidationError
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.clients import (
    ClientCreate,
    ClientImportResult,
    ClientListResponse,
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
    query: str = Query("", alias="q"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ClientListResponse:
    effective_include_deleted = include_deleted and tenant_ctx.role == "admin"
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


@router.post(
    "/import",
    response_model=ClientImportResult,
    summary="Importer des clients depuis un CSV",
    description="Importe des clients en lot depuis un fichier CSV (separateur point-virgule).",
)
async def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ClientImportResult:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise ValidationError("file", "Le fichier doit etre au format CSV.")
    content = await file.read()
    return client_service.import_from_csv(
        db,
        tenant_id=tenant_ctx.tenant_id,
        file_content=content,
        user_id=tenant_ctx.user_id,
    )


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
    tenant_ctx: TenantContext = Depends(get_tenant_context),
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
    tenant_ctx: TenantContext = Depends(get_tenant_context),
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
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_tenant_role("admin", "manager")),
) -> dict[str, str]:
    client_service.delete_client(db, tenant_id=tenant_ctx.tenant_id, client_id=client_id, user_id=tenant_ctx.user_id)
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
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> dict[str, str]:
    allowed = {"image/jpeg", "image/png", "image/jpg"}
    if file.content_type not in allowed:
        raise ValidationError("file", "Le fichier doit etre une image (JPG ou PNG).")
    file_data = await file.read()
    max_size = 5 * 1024 * 1024
    if len(file_data) > max_size:
        raise ValidationError("file", "L'image ne doit pas depasser 5 Mo.")
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
