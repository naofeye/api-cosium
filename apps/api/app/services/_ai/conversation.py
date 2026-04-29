"""Service haute-niveau pour l'historique conversationnel du copilote IA.

Fonctions :
- create_conversation_with_message : cree une conversation + sauvegarde 1er Q/R
- append_to_conversation : ajoute Q user puis R assistant a une conversation existante
- list_conversations / get_conversation_with_messages / delete_conversation

Le service est dissocie du copilote core (ai_service.copilot_query) pour :
1. Pouvoir sauvegarder l'historique meme si l'appel IA echoue (l'erreur est stockee
   comme message role="error")
2. Permettre de "rejouer" une conversation : on charge l'historique, on le passe au
   provider Claude pour qu'il ait le contexte des Q/R precedentes.
"""

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.integrations.ai.claude_provider import claude_provider
from app.repositories import ai_conversation_repo, ai_usage_repo
from app.services._ai.context import resolve_copilot_context

logger = get_logger("ai_conversation_service")


def _estimate_cost(tokens_in: int, tokens_out: int) -> float:
    return round((tokens_in * 0.00000025) + (tokens_out * 0.00000125), 6)


def _truncate_title(question: str) -> str:
    """Genere un titre lisible a partir de la 1ere question (max 80 chars)."""
    title = question.strip().split("\n")[0][:80]
    return title or "Nouvelle conversation"


def _build_history_messages(db: Session, conversation_id: int, tenant_id: int) -> list[dict]:
    """Charge l'historique d'une conversation au format messages Anthropic.

    On filtre les messages role="error" (ils ne sont pas du contenu user/assistant).
    """
    messages = ai_conversation_repo.list_messages(db, conversation_id, tenant_id)
    return [
        {"role": m.role, "content": m.content}
        for m in messages
        if m.role in ("user", "assistant")
    ]


def append_message(
    db: Session,
    *,
    tenant_id: int,
    user_id: int,
    question: str,
    conversation_id: int | None,
    mode: str,
    case_id: int | None,
) -> tuple[int, str]:
    """Ajoute un Q/R a une conversation (ou en cree une si conversation_id=None).

    Returns:
        (conversation_id, assistant_text)
    """
    # 1. Resoudre/creer la conversation
    if conversation_id is None:
        conversation = ai_conversation_repo.create(
            db,
            tenant_id=tenant_id,
            user_id=user_id,
            mode=mode,
            case_id=case_id,
            title=_truncate_title(question),
        )
        history: list[dict] = []
    else:
        conversation = ai_conversation_repo.get_by_id(db, conversation_id, tenant_id)
        if not conversation:
            from app.core.exceptions import NotFoundError
            raise NotFoundError("ai_conversation", conversation_id)
        history = _build_history_messages(db, conversation.id, tenant_id)

    # 2. Sauver immediatement la question utilisateur
    ai_conversation_repo.add_message(db, conversation, role="user", content=question)
    db.commit()

    # 3. Construire le contexte (system prompt + RAG/dossier)
    system, context = resolve_copilot_context(db, tenant_id, conversation.mode, question, conversation.case_id)

    # 4. Appel Claude avec historique
    try:
        result = claude_provider.query_with_usage(
            question, context=context, system=system, history=history,
        )
        assistant_text = result.get("text", "")
        tokens_in = result.get("tokens_in", 0)
        tokens_out = result.get("tokens_out", 0)
        model_used = result.get("model", "unknown")
    except Exception as exc:
        # Sauver l'erreur comme message role="error" pour audit
        err_msg = f"Erreur IA : {exc}"
        ai_conversation_repo.add_message(db, conversation, role="error", content=err_msg)
        db.commit()
        logger.error(
            "ai_conversation_append_failed",
            conversation_id=conversation.id,
            tenant_id=tenant_id,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        raise

    # 5. Sauver la reponse assistant
    ai_conversation_repo.add_message(
        db, conversation,
        role="assistant",
        content=assistant_text,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )

    # 6. Logger l'usage IA (billing)
    ai_usage_repo.create(
        db,
        tenant_id=tenant_id,
        user_id=user_id,
        copilot_type=conversation.mode,
        model_used=model_used,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=_estimate_cost(tokens_in, tokens_out),
    )

    db.commit()
    logger.info(
        "ai_conversation_message_appended",
        conversation_id=conversation.id,
        tenant_id=tenant_id,
        user_id=user_id,
        mode=conversation.mode,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )
    return conversation.id, assistant_text
