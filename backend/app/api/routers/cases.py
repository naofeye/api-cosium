from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.audit import CompletenessResponse
from app.domain.schemas.cases import CaseCreate, CaseDetail, CaseResponse
from app.services import case_service, completeness_service

router = APIRouter(prefix="/api/v1", tags=["cases"])


@router.get("/cases", response_model=list[CaseResponse])
def list_cases(
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> list[CaseResponse]:
    return case_service.list_cases(db, tenant_id=tenant_ctx.tenant_id, limit=limit, offset=offset)


@router.post("/cases", response_model=CaseResponse, status_code=201)
def create_case(
    payload: CaseCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CaseResponse:
    return case_service.create_case(db, tenant_id=tenant_ctx.tenant_id, payload=payload, user_id=tenant_ctx.user_id)


@router.get("/cases/{case_id}", response_model=CaseDetail)
def get_case(
    case_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CaseDetail:
    return case_service.get_case_detail(db, tenant_id=tenant_ctx.tenant_id, case_id=case_id)


@router.get("/cases/{case_id}/completeness", response_model=CompletenessResponse)
def get_completeness(
    case_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CompletenessResponse:
    return completeness_service.get_completeness(db, tenant_id=tenant_ctx.tenant_id, case_id=case_id)
