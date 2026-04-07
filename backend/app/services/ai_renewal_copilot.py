"""Copilote IA pour le renouvellement — generation de messages personnalises."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.integrations.ai.claude_provider import claude_provider
from app.models import Customer
from app.repositories import ai_context_repo, ai_usage_repo

logger = get_logger("ai_renewal_copilot")

RENEWAL_SYSTEM_PROMPT = (
    "Tu es le Copilote Renouvellement d'OptiFlow, une plateforme pour opticiens. "
    "Tu generes des messages de relance personnalises pour inciter les clients "
    "a renouveler leur equipement optique (lunettes, verres, lentilles). "
    "Le ton doit etre chaleureux, professionnel et bienveillant. "
    "Mentionne l'importance de la sante visuelle. "
    "Adapte le message au canal (email = plus long et formel, SMS = court et direct). "
    "Reponds UNIQUEMENT avec le texte du message, sans commentaire ni explication."
)


def generate_renewal_message(
    db: Session,
    tenant_id: int,
    customer_id: int,
    channel: str = "email",
    months_since: int = 24,
    equipment_type: str | None = None,
    has_mutuelle: bool = False,
) -> str:
    """Genere un message de renouvellement personnalise via IA pour un client."""

    customer = db.get(Customer, customer_id)
    if not customer or customer.tenant_id != tenant_id:
        return ""

    context_parts = [
        f"CLIENT : {customer.first_name} {customer.last_name}",
        f"Dernier achat : il y a {months_since} mois",
    ]
    if equipment_type:
        context_parts.append(f"Type d'equipement : {equipment_type}")
    if has_mutuelle:
        context_parts.append("Le client a une mutuelle active (reste a charge reduit)")
    if customer.email:
        context_parts.append(f"Email : {customer.email}")

    context = "\n".join(context_parts)

    prompt = f"Genere un message de {channel} pour inviter ce client a renouveler son equipement optique. "
    if channel == "sms":
        prompt += "Le SMS doit faire moins de 160 caracteres."
    else:
        prompt += "L'email doit etre court (3-4 phrases max), avec un objet et un corps."

    result = claude_provider.query_with_usage(
        prompt,
        context=context,
        system=RENEWAL_SYSTEM_PROMPT,
    )

    # Log usage
    _log_ai_usage(db, tenant_id, result)

    logger.info(
        "renewal_message_generated",
        tenant_id=tenant_id,
        customer_id=customer_id,
        channel=channel,
    )

    return result["text"]


def generate_renewal_template(
    db: Session,
    tenant_id: int,
    channel: str = "email",
) -> str | None:
    """Genere un template generique de renouvellement (avec placeholders)."""

    prompt = (
        f"Genere un template de message de renouvellement en {channel} pour des opticiens. "
        f"Utilise les placeholders suivants : "
        f"{{{{client_name}}}} pour le nom du client, "
        f"{{{{prenom}}}} pour le prenom. "
    )
    if channel == "sms":
        prompt += "Le SMS doit faire moins de 160 caracteres."
    else:
        prompt += (
            "L'email doit etre court (3-4 phrases), chaleureux et professionnel. "
            "Mentionne l'importance du renouvellement pour la sante visuelle."
        )

    result = claude_provider.query_with_usage(
        prompt,
        context="",
        system=RENEWAL_SYSTEM_PROMPT,
    )

    _log_ai_usage(db, tenant_id, result)
    return result["text"]


def analyze_renewal_potential(
    db: Session,
    tenant_id: int,
    total_opportunities: int,
    high_score_count: int,
    avg_months: float,
    estimated_revenue: float,
) -> str:
    """Analyse IA mensuelle du potentiel de renouvellement."""

    total_clients = db.scalar(select(func.count()).select_from(Customer).where(Customer.tenant_id == tenant_id)) or 0

    context = (
        f"ANALYSE RENOUVELLEMENT — RESUME MENSUEL\n"
        f"Total clients en base : {total_clients}\n"
        f"Opportunites de renouvellement detectees : {total_opportunities}\n"
        f"Opportunites a fort potentiel (score >= 70) : {high_score_count}\n"
        f"Anciennete moyenne du dernier achat : {avg_months:.1f} mois\n"
        f"Chiffre d'affaires potentiel estime : {estimated_revenue:.2f} EUR\n"
    )

    prompt = (
        "Analyse ce potentiel de renouvellement et donne des recommandations "
        "strategiques a l'opticien : priorites, timing, canaux de contact, "
        "et estimation du taux de conversion attendu. Sois concis (5-8 phrases)."
    )

    system = (
        "Tu es un consultant en strategie commerciale specialise dans l'optique. "
        "Analyse les donnees de renouvellement et donne des recommandations concretes. "
        "Reponds en francais."
    )

    result = claude_provider.query_with_usage(prompt, context=context, system=system)
    _log_ai_usage(db, tenant_id, result)
    return result["text"]


def _log_ai_usage(db: Session, tenant_id: int, result: dict, user_id: int = 0) -> None:
    """Enregistre l'utilisation IA."""
    if not user_id:
        logger.warning("operation_without_user_id", action="log_ai_usage", entity="ai_usage")
    try:
        usage = AiUsageLog(
            tenant_id=tenant_id,
            user_id=user_id,
            copilot_type="renouvellement",
            model_used=result.get("model", "unknown"),
            tokens_in=result.get("tokens_in", 0),
            tokens_out=result.get("tokens_out", 0),
            cost_usd=_estimate_cost(result.get("tokens_in", 0), result.get("tokens_out", 0)),
        )
        db.add(usage)
        db.commit()
    except (SQLAlchemyError, ValueError, TypeError) as e:
        logger.warning("ai_usage_log_failed", error=str(e))


def _estimate_cost(tokens_in: int, tokens_out: int) -> float:
    return round((tokens_in * 0.00000025) + (tokens_out * 0.00000125), 6)
