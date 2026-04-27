import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.integrations.ai.claude_provider import claude_provider
from app.repositories import ai_context_repo
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

    cosium_ctx = ai_service.get_client_cosium_context(db, customer_id, tenant_ctx.tenant_id)
    if not cosium_ctx:
        return PreRdvBriefResponse(
            customer_id=customer_id,
            brief=(
                f"Aucune donnee Cosium synchronisee pour {customer.first_name} {customer.last_name}. "
                "Preparez le RDV manuellement."
            ),
            context_used=False,
        )

    system = (
        "Tu es l'assistant de l'opticien. Resume en 5-8 points le dossier client pour preparer un RDV : "
        "dernier equipement et date, evolution des dioptries si notable, PEC en attente, solde impaye, "
        "points de vigilance. Francais clair, pas de jargon technique, max 150 mots."
    )
    question = f"Prepare un brief pour le RDV de {customer.first_name} {customer.last_name}."
    result = claude_provider.query_with_usage(question, context=cosium_ctx, system=system)
    return PreRdvBriefResponse(
        customer_id=customer_id,
        brief=result.get("text", ""),
        context_used=True,
    )


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

    cosium_ctx = ai_service.get_client_cosium_context(db, customer_id, tenant_ctx.tenant_id)
    if not cosium_ctx:
        return UpsellSuggestionResponse(
            customer_id=customer_id,
            suggestion="Pas d'historique suffisant pour une suggestion d'upsell.",
            context_used=False,
        )

    system = (
        "Tu es le conseiller commercial de l'opticien. "
        "A partir de l'historique client (dernier equipement, prescriptions, dioptries), "
        "propose UN seul upsell pertinent et realiste : verres progressifs si addition >= +1.00, "
        "anti-lumiere bleue si profession ecran probable, seconde paire solaire si pas solaire, "
        "lentilles si myopie moderee. "
        "Format : 1 ligne d'accroche + 3 bullets max justifiant. Francais chaleureux, pas de jargon."
    )
    question = f"Suggere un upsell pertinent pour {customer.first_name} {customer.last_name}."
    result = claude_provider.query_with_usage(question, context=cosium_ctx, system=system)
    return UpsellSuggestionResponse(
        customer_id=customer_id,
        suggestion=result.get("text", ""),
        context_used=True,
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

    cosium_ctx = ai_service.get_client_cosium_context(db, customer_id, tenant_ctx.tenant_id)
    if not cosium_ctx:
        return ProductRecommendationResponse(
            customer_id=customer_id,
            recommendation="Aucune prescription synchronisee, impossible de proposer une recommandation adaptee.",
            context_used=False,
        )

    system = (
        "Tu es l'expert optique du magasin. A partir des dernieres dioptries du client, "
        "recommande : (1) type de verre ideal (unifocaux / progressifs / occupationnels), "
        "(2) traitements indispensables (anti-reflet, anti-lumiere bleue, durci, photochromique), "
        "(3) materiau adapte (indice >=1.6 si sphere >=+3 ou <=-3, sinon 1.5). "
        "Justifie chaque point par UN parametre precis de la prescription. "
        "Format : liste markdown, max 5 bullets, francais clair."
    )
    question = f"Quel equipement conseiller a {customer.first_name} {customer.last_name} ?"
    result = claude_provider.query_with_usage(question, context=cosium_ctx, system=system)
    return ProductRecommendationResponse(
        customer_id=customer_id,
        recommendation=result.get("text", ""),
        context_used=True,
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
    devis, lignes, customer_id = ai_context_repo.get_devis_with_lines(
        db, devis_id, tenant_ctx.tenant_id
    )
    if not devis:
        raise HTTPException(status_code=404, detail="Devis introuvable")

    lignes_text = "\n".join(
        f"- {l.designation} x{l.quantite} @ {l.prix_unitaire_ht}EUR HT" for l in lignes
    ) or "(aucune ligne)"

    customer_ctx = ""
    if customer_id:
        customer_ctx = ai_service.get_client_cosium_context(
            db, customer_id, tenant_ctx.tenant_id
        ) or ""

    context = (
        f"DEVIS #{devis.numero} - Total TTC {devis.montant_ttc}EUR\n"
        f"Part Secu {devis.part_secu}EUR, Part mutuelle {devis.part_mutuelle}EUR, "
        f"Reste a charge {devis.reste_a_charge}EUR\n"
        f"Lignes:\n{lignes_text}\n"
        f"\n--- HISTORIQUE CLIENT ---\n{customer_ctx}" if customer_ctx else ""
    )

    system = (
        "Tu es l'assistant qualite de l'opticien. Analyse le devis en 4-5 bullets : "
        "1) Coherence prescription vs verres, 2) Options manquantes (traitement, anti-reflet), "
        "3) Prix par rapport au marche, 4) Points de vigilance pour le client. "
        "Termine par une liste courte de WARNINGS si incoherence grave. Francais professionnel."
    )
    question = f"Analyse le devis #{devis.numero}."
    result = claude_provider.query_with_usage(question, context=context, system=system)
    response_text = result.get("text", "")

    # Extraction des warnings
    warnings: list[str] = []
    for line in response_text.split("\n"):
        stripped = line.strip()
        if stripped.lower().startswith(("warning:", "attention:", "alerte:")):
            warnings.append(stripped)

    return DevisAnalysisResponse(
        devis_id=devis_id,
        analysis=response_text,
        warnings=warnings,
    )
