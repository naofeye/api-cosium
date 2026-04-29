"""Service IA — copilote metier OptiFlow avec 4 modes.

Ce module expose l'API publique du copilote IA. Les details d'implementation
sont organises en sous-modules prives `_ai.{prompts,context,client_features}` :

- `_ai.prompts`         : SYSTEM_PROMPTS pour les 4 modes (dossier, financier, documentaire, marketing)
- `_ai.context`         : construction du contexte (Cosium customer, dossier, RAG documentaire)
- `_ai.client_features` : fonctions IA orientees client (brief RDV, upsell, recommandation, analyse devis)
"""

from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.integrations.ai.claude_provider import claude_provider
from app.integrations.ai.rag import search_docs  # noqa: F401 — re-export tests
from app.repositories import (
    ai_context_repo,  # noqa: F401 — re-export tests
    ai_usage_repo,
)
from app.services._ai.client_features import (
    devis_analysis,
    pre_rdv_brief,
    product_recommendation,
    upsell_suggestion,
)
from app.services._ai.context import (
    _build_case_context,  # noqa: F401 — re-export pour compat tests
    get_client_cosium_context,
    resolve_copilot_context,
)
from app.services._ai.prompts import SYSTEM_PROMPTS

logger = get_logger("ai_service")

__all__ = [
    "SYSTEM_PROMPTS",
    "copilot_query",
    "copilot_stream",
    "devis_analysis",
    "get_client_cosium_context",
    "pre_rdv_brief",
    "product_recommendation",
    "upsell_suggestion",
]


def _estimate_cost(tokens_in: int, tokens_out: int) -> float:
    """Estimation du cout basee sur les tarifs Haiku."""
    return round((tokens_in * 0.00000025) + (tokens_out * 0.00000125), 6)


def copilot_query(
    db: Session,
    tenant_id: int,
    question: str,
    user_id: int,
    case_id: int | None = None,
    mode: str = "dossier",
) -> str:
    """Point d'entree principal du copilote IA."""
    system, context = resolve_copilot_context(db, tenant_id, mode, question, case_id)

    logger.info("copilot_query", tenant_id=tenant_id, mode=mode, case_id=case_id, question_len=len(question))
    result = claude_provider.query_with_usage(question, context=context, system=system)

    ai_usage_repo.create(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        copilot_type=mode,
        model_used=result.get("model", "unknown"),
        tokens_in=result.get("tokens_in", 0),
        tokens_out=result.get("tokens_out", 0),
        cost_usd=_estimate_cost(result.get("tokens_in", 0), result.get("tokens_out", 0)),
    )

    return result["text"]


def copilot_stream(
    db: Session,
    tenant_id: int,
    question: str,
    user_id: int,
    case_id: int | None = None,
    mode: str = "dossier",
) -> Iterator[dict]:
    """Version streaming du copilote IA.

    Yields des dicts identiques a `claude_provider.query_stream` :
    - {"type": "chunk", "text": "..."} pendant la generation
    - {"type": "done", "tokens_in": int, "tokens_out": int, "model": str} a la fin
    - {"type": "error", "error": str} en cas d'echec

    L'usage IA est loggue en BDD apres reception de l'evenement "done".
    """
    system, context = resolve_copilot_context(db, tenant_id, mode, question, case_id)

    logger.info(
        "copilot_stream",
        tenant_id=tenant_id,
        mode=mode,
        case_id=case_id,
        question_len=len(question),
    )

    tokens_in = 0
    tokens_out = 0
    model_used = "unknown"

    for event in claude_provider.query_stream(question, context=context, system=system):
        if event.get("type") == "done":
            tokens_in = event.get("tokens_in", 0)
            tokens_out = event.get("tokens_out", 0)
            model_used = event.get("model", "unknown")
        yield event

    ai_usage_repo.create(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        copilot_type=mode,
        model_used=model_used,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=_estimate_cost(tokens_in, tokens_out),
    )
