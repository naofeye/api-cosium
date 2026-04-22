from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_permission
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.audit import CompletenessResponse
from app.domain.schemas.cases import CaseCreate, CaseDetail, CaseResponse
from app.services import case_service, completeness_service

router = APIRouter(prefix="/api/v1", tags=["cases"])


@router.get(
    "/cases",
    response_model=list[CaseResponse],
    summary="Lister les dossiers",
    description="Retourne la liste paginee des dossiers clients.",
)
def list_cases(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[CaseResponse]:
    offset = (page - 1) * page_size
    return case_service.list_cases(db, tenant_id=tenant_ctx.tenant_id, limit=page_size, offset=offset)


@router.post(
    "/cases",
    response_model=CaseResponse,
    status_code=201,
    summary="Creer un dossier",
    description="Cree un nouveau dossier client.",
)
def create_case(
    payload: CaseCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_permission("create", "case")),
) -> CaseResponse:
    return case_service.create_case(db, tenant_id=tenant_ctx.tenant_id, payload=payload, user_id=tenant_ctx.user_id)


@router.get(
    "/cases/{case_id}",
    response_model=CaseDetail,
    summary="Detail d'un dossier",
    description="Retourne le detail complet d'un dossier avec ses documents et paiements.",
)
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CaseDetail:
    return case_service.get_case_detail(db, tenant_id=tenant_ctx.tenant_id, case_id=case_id)


@router.get(
    "/cases/{case_id}/completeness",
    response_model=CompletenessResponse,
    summary="Completude d'un dossier",
    description="Retourne le score de completude et les elements manquants du dossier.",
)
def get_completeness(
    case_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CompletenessResponse:
    return completeness_service.get_completeness(db, tenant_id=tenant_ctx.tenant_id, case_id=case_id)
