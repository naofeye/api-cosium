from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.core.deps import require_permission
from app.core.tenant_context import TenantContext, get_tenant_context
from app.db.session import get_db
from app.domain.schemas.interactions import (
    EmailPayload,
    InteractionCreate,
    InteractionListResponse,
    InteractionResponse,
)
from app.integrations.email_sender import email_sender
from app.repositories import client_repo
from app.services import (
    client_timeline_service,
    interaction_service,
)

router = APIRouter(prefix="/api/v1", tags=["client-360"])


@router.get(
    "/clients/{client_id}/interactions",
    response_model=InteractionListResponse,
    summary="Historique des interactions",
    description="Retourne la chronologie des interactions avec un client.",
)
def list_interactions(
    client_id: int,
    type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> InteractionListResponse:
    items, total = interaction_service.get_client_timeline(
        db,
        tenant_id=tenant_ctx.tenant_id,
        client_id=client_id,
        type=type,
        limit=limit,
    )
    return InteractionListResponse(items=items, total=total)


@router.get(
    "/clients/{client_id}/timeline",
    summary="Timeline unifiee cross-canal",
    description=(
        "Agrege interactions et messages marketing (campagnes envoyees) dans une chronologie "
        "unique triee descendant. Filtre par kinds si specifie."
    ),
)
def client_timeline(
    client_id: int,
    kinds: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    events = client_timeline_service.build_client_timeline(
        db,
        tenant_id=tenant_ctx.tenant_id,
        customer_id=client_id,
        kinds=kinds,
    )
    return {"client_id": client_id, "events": events, "total": len(events)}


@router.post(
    "/interactions",
    response_model=InteractionResponse,
    status_code=201,
    summary="Ajouter une interaction",
    description="Enregistre une nouvelle interaction avec un client.",
)
def create_interaction(
    payload: InteractionCreate,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_permission("create", "interaction")),
) -> InteractionResponse:
    return interaction_service.add_interaction(
        db,
        tenant_id=tenant_ctx.tenant_id,
        payload=payload,
        user_id=tenant_ctx.user_id,
    )


@router.delete(
    "/interactions/{interaction_id}",
    status_code=200,
    summary="Supprimer une interaction",
    description="Supprime une interaction du journal.",
)
def delete_interaction(
    interaction_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_permission("delete", "interaction")),
) -> dict[str, str]:
    interaction_service.delete_interaction(
        db,
        tenant_id=tenant_ctx.tenant_id,
        interaction_id=interaction_id,
        user_id=tenant_ctx.user_id,
    )
    return {"message": "Interaction supprimee avec succes"}


@router.post(
    "/clients/{client_id}/send-email",
    status_code=200,
    summary="Envoyer un email a un client",
    description="Envoie un email au client et enregistre une interaction de type email.",
)
def send_email_to_client(
    client_id: int,
    payload: EmailPayload,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(require_permission("create", "interaction")),
) -> dict[str, str]:
    customer = client_repo.get_by_id_active(db, client_id=client_id, tenant_id=tenant_ctx.tenant_id)
    if not customer:
        raise NotFoundError("client", client_id)
    if not customer.email:
        raise ValidationError("email", "Ce client n'a pas d'adresse email renseignee.")

    body_html = payload.body.replace("\n", "<br>")
    success = email_sender.send_email(to=payload.to, subject=payload.subject, body_html=body_html)
    if not success:
        raise ValidationError("email", "L'envoi de l'email a echoue. Veuillez reessayer.")

    interaction_payload = InteractionCreate(
        client_id=client_id,
        type="email",
        direction="sortant",
        subject=payload.subject,
        content=payload.body,
    )
    interaction_service.add_interaction(
        db,
        tenant_id=tenant_ctx.tenant_id,
        payload=interaction_payload,
        user_id=tenant_ctx.user_id,
    )

    return {"message": "Email envoye avec succes"}


@router.get(
    "/clients/{client_id}/ai-renewal-suggestion",
    summary="IA : suggestion de relance renouvellement",
    description="Genere un message contextualise base sur score, derniere visite, equipement.",
)
def ai_renewal_suggestion(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    """Suggestion textuelle simple basee sur les donnees client + score."""
    from app.services import analytics_cosium_extras

    customer = client_repo.get_by_id(db, client_id, tenant_ctx.tenant_id)
    if not customer:
        raise NotFoundError("Client", client_id)

    score = analytics_cosium_extras.compute_client_score(db, tenant_ctx.tenant_id, client_id)
    days_since = score.get("days_since_last_invoice")
    months = (days_since // 30) if days_since else 0

    if not score["is_renewable"]:
        suggestion = (
            f"{customer.first_name} {customer.last_name} a achete il y a {months} mois — "
            "renouvellement pas encore opportun. Continuer le suivi."
        )
        urgency = "low"
    elif score["category"] == "VIP":
        suggestion = (
            f"{customer.first_name} {customer.last_name} (VIP, CA 12m {score['ca_12m']:.0f}€) — "
            f"dernier achat il y a {months} mois. Proposer un bilan visuel premium + nouveaute monture haut de gamme. "
            "Appel personnel recommande."
        )
        urgency = "high"
    elif score["category"] == "Fidele":
        suggestion = (
            f"Client fidele, dernier achat il y a {months} mois. "
            "Email de relance avec offre renouvellement (-10% ou bilan offert) recommande."
        )
        urgency = "medium"
    else:
        suggestion = (
            f"Client standard, dernier achat il y a {months} mois. "
            "SMS automatique de rappel bilan visuel."
        )
        urgency = "medium"

    return {
        "customer_id": client_id,
        "customer_name": f"{customer.first_name} {customer.last_name}",
        "score": score["score"],
        "category": score["category"],
        "months_since_last_purchase": months,
        "suggestion": suggestion,
        "urgency": urgency,
    }


@router.get(
    "/clients/{client_id}/score",
    summary="Score client (algo 0-100)",
    description="Calcule un score client (CA, frequence, anciennete, mutuelle, impayes, eligibilite renouvellement). Categorie VIP/Fidele/Standard/Nouveau.",
)
def get_client_score(
    client_id: int,
    db: Session = Depends(get_db),
    tenant_ctx: TenantContext = Depends(get_tenant_context),
) -> dict:
    from app.services import analytics_cosium_extras
    return analytics_cosium_extras.compute_client_score(db, tenant_ctx.tenant_id, client_id)
