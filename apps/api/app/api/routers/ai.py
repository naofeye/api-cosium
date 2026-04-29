import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.ai_conversation import (
    AiAppendRequest,
    AiAppendResponse,
    AiConversationDetail,
    AiConversationListItem,
    AiMessageResponse,
)
from app.repositories import ai_context_repo, ai_conversation_repo
from app.services import ai_service
from app.services._ai.conversation import append_message

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


def _format_sse_event(event: dict) -> str:
    """Convertit un dict d'evenement en frame SSE conforme."""
    event_type = event.get("type", "chunk")
    data = {k: v for k, v in event.items() if k != "type"}
    payload = json.dumps(data, ensure_ascii=False)
    return f"event: {event_type}\ndata: {payload}\n\n"


@router.post(
    "/copilot/stream",
    summary="Interroger le copilote IA en streaming SSE",
    description=(
        "Pose une question au copilote IA et streame la reponse en Server-Sent Events. "
        "Chaque chunk est emis sous forme d'event SSE `chunk` ; un event final `done` "
        "(ou `error`) cloture le flux."
    ),
)
def copilot_stream(
    payload: CopilotQuery,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> StreamingResponse:
    def event_generator() -> Iterator[str]:
        for event in ai_service.copilot_stream(
            db,
            tenant_id=tenant_ctx.tenant_id,
            question=payload.question,
            case_id=payload.case_id,
            mode=payload.mode,
            user_id=tenant_ctx.user_id,
        ):
            yield _format_sse_event(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


class PreRdvBriefResponse(BaseModel):
    customer_id: int
    brief: str
    context_used: bool


@router.get(
    "/client/{customer_id}/pre-rdv-brief",
    response_model=PreRdvBriefResponse,
    summary="Brief IA avant RDV client",
    description=(
        "Genere un resume concis pour preparer un RDV : dernier achat, prescription actuelle, "
        "PEC en cours, points d'attention. Utilise les donnees Cosium synchronisees."
    ),
)
def pre_rdv_brief(
    customer_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> PreRdvBriefResponse:
    customer = ai_context_repo.get_customer_by_id(db, customer_id, tenant_ctx.tenant_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Client introuvable")

    brief_text, context_used = ai_service.pre_rdv_brief(db, customer_id, tenant_ctx.tenant_id)
    if not context_used:
        brief_text = (
            f"Aucune donnee Cosium synchronisee pour {customer.first_name} {customer.last_name}. "
            "Preparez le RDV manuellement."
        )
    return PreRdvBriefResponse(customer_id=customer_id, brief=brief_text, context_used=context_used)


class UpsellSuggestionResponse(BaseModel):
    customer_id: int
    suggestion: str
    context_used: bool


@router.get(
    "/client/{customer_id}/upsell-suggestion",
    response_model=UpsellSuggestionResponse,
    summary="Suggestion d'upsell basee sur les equipements du client",
    description=(
        "Analyse les dernieres factures et prescriptions pour proposer un upsell pertinent "
        "(verres progressifs, anti-lumiere bleue, seconde paire, etc.)."
    ),
)
def upsell_suggestion(
    customer_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> UpsellSuggestionResponse:
    customer = ai_context_repo.get_customer_by_id(db, customer_id, tenant_ctx.tenant_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Client introuvable")

    suggestion_text, context_used = ai_service.upsell_suggestion(db, customer_id, tenant_ctx.tenant_id)
    if not context_used:
        suggestion_text = "Pas d'historique suffisant pour une suggestion d'upsell."
    return UpsellSuggestionResponse(
        customer_id=customer_id, suggestion=suggestion_text, context_used=context_used
    )


class ReimbursementSimulationRequest(BaseModel):
    prix_monture: float = Field(0.0, ge=0)
    prix_verre_od: float = Field(0.0, ge=0)
    prix_verre_og: float = Field(0.0, ge=0)
    sphere_od: float | None = None
    cylindre_od: float | None = None
    addition_od: float | None = None
    sphere_og: float | None = None
    cylindre_og: float | None = None
    addition_og: float | None = None
    mutuelle_pct_verres: float = Field(100.0, ge=0, le=500)
    mutuelle_forfait_monture: float = Field(100.0, ge=0)
    classe_a: bool = False


@router.post(
    "/simulate-reimbursement",
    summary="Simulation remboursement optique",
    description=(
        "Calcule une estimation du remboursement SS+Mutuelle pour un equipement lunettes. "
        "Heuristique simple : BR selon complexite dioptrique, 60% SS, pct/forfait mutuelle."
    ),
)
def simulate_reimbursement(
    payload: ReimbursementSimulationRequest,
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    from app.services import reimbursement_simulation_service

    return reimbursement_simulation_service.simulate_reimbursement(**payload.model_dump())


class ProductRecommendationResponse(BaseModel):
    customer_id: int
    recommendation: str
    context_used: bool


@router.get(
    "/client/{customer_id}/product-recommendation",
    response_model=ProductRecommendationResponse,
    summary="Recommandation produit basee sur prescription",
    description=(
        "Suggere des types de verres/montures/traitements adaptes a la derniere prescription. "
        "Utilise les dioptries synchronisees."
    ),
)
def product_recommendation(
    customer_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> ProductRecommendationResponse:
    customer = ai_context_repo.get_customer_by_id(db, customer_id, tenant_ctx.tenant_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Client introuvable")

    rec_text, context_used = ai_service.product_recommendation(db, customer_id, tenant_ctx.tenant_id)
    if not context_used:
        rec_text = "Aucune prescription synchronisee, impossible de proposer une recommandation adaptee."
    return ProductRecommendationResponse(
        customer_id=customer_id, recommendation=rec_text, context_used=context_used
    )


class DevisAnalysisResponse(BaseModel):
    devis_id: int
    analysis: str
    warnings: list[str]


@router.get(
    "/devis/{devis_id}/analysis",
    response_model=DevisAnalysisResponse,
    summary="Analyse IA coherence devis",
    description=(
        "Analyse la coherence d'un devis vs la prescription client. "
        "Detecte verres sous-adaptes, options manquantes, prix anormaux."
    ),
)
def devis_analysis(
    devis_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> DevisAnalysisResponse:
    result = ai_service.devis_analysis(db, devis_id, tenant_ctx.tenant_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Devis introuvable")
    analysis_text, warnings = result
    return DevisAnalysisResponse(devis_id=devis_id, analysis=analysis_text, warnings=warnings)


# ---------------------------------------------------------------------------
# Conversational chat history (persisted)
# ---------------------------------------------------------------------------

@router.get(
    "/conversations",
    response_model=list[AiConversationListItem],
    summary="Lister mes conversations IA",
    description="Retourne les conversations de l'utilisateur courant, triees par date de mise a jour.",
)
def list_conversations(
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
    limit: int = 30,
    offset: int = 0,
) -> list[AiConversationListItem]:
    rows = ai_conversation_repo.list_by_user(
        db, tenant_id=tenant_ctx.tenant_id, user_id=tenant_ctx.user_id, limit=limit, offset=offset
    )
    return [AiConversationListItem.model_validate(c) for c in rows]


@router.get(
    "/conversations/{conversation_id}",
    response_model=AiConversationDetail,
    summary="Detail d'une conversation IA",
    description="Retourne la conversation et tous ses messages (user/assistant/error).",
)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> AiConversationDetail:
    conv = ai_conversation_repo.get_by_id(db, conversation_id, tenant_ctx.tenant_id)
    if not conv or conv.user_id != tenant_ctx.user_id:
        # Pas de leak : meme reponse pour "n'existe pas" et "appartient a un autre user"
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    messages = ai_conversation_repo.list_messages(db, conv.id, tenant_ctx.tenant_id)
    return AiConversationDetail(
        id=conv.id,
        title=conv.title,
        mode=conv.mode,
        case_id=conv.case_id,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[AiMessageResponse.model_validate(m) for m in messages],
    )


@router.post(
    "/conversations/append",
    response_model=AiAppendResponse,
    summary="Ajouter un message a une conversation IA (cree si conversation_id absent)",
    description=(
        "Sauvegarde la question utilisateur, appelle Claude avec l'historique, "
        "sauvegarde la reponse, retourne (conversation_id, answer)."
    ),
)
def append_conversation_message(
    payload: AiAppendRequest,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> AiAppendResponse:
    if payload.conversation_id is not None:
        # Verifier la propriete avant d'appeler le service
        conv = ai_conversation_repo.get_by_id(db, payload.conversation_id, tenant_ctx.tenant_id)
        if not conv or conv.user_id != tenant_ctx.user_id:
            raise HTTPException(status_code=404, detail="Conversation introuvable")

    try:
        conv_id, answer = append_message(
            db,
            tenant_id=tenant_ctx.tenant_id,
            user_id=tenant_ctx.user_id,
            question=payload.question,
            conversation_id=payload.conversation_id,
            mode=payload.mode,
            case_id=payload.case_id,
        )
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AiAppendResponse(conversation_id=conv_id, answer=answer)


@router.delete(
    "/conversations/{conversation_id}",
    status_code=204,
    summary="Supprimer une conversation IA (soft-delete)",
)
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> None:
    conv = ai_conversation_repo.get_by_id(db, conversation_id, tenant_ctx.tenant_id)
    if not conv or conv.user_id != tenant_ctx.user_id:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    ai_conversation_repo.soft_delete(db, conversation_id, tenant_ctx.tenant_id)
    db.commit()
