from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.services import ai_service

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


class CopilotQuery(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    case_id: int | None = None
    mode: str = Field("dossier", pattern="^(dossier|financier|documentaire|marketing)$")


class CopilotResponse(BaseModel):
    response: str
    mode: str
    case_id: int | None = None


@router.post(
    "/copilot/query",
    response_model=CopilotResponse,
    summary="Interroger le copilote IA",
    description="Pose une question au copilote IA dans un contexte metier.",
)
def copilot_query(
    payload: CopilotQuery,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> CopilotResponse:
    result = ai_service.copilot_query(
        db,
        tenant_id=tenant_ctx.tenant_id,
        question=payload.question,
        case_id=payload.case_id,
        mode=payload.mode,
        user_id=tenant_ctx.user_id,
    )
    return CopilotResponse(
        response=result,
        mode=payload.mode,
        case_id=payload.case_id,
    )
