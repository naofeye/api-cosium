"""Repository pour les conversations IA persistees (historique copilote)."""

from datetime import UTC, datetime

from sqlalchemy import desc, select, update
from sqlalchemy.orm import Session

from app.models.ai import AiConversation, AiMessage


def create(
    db: Session,
    tenant_id: int,
    user_id: int,
    mode: str,
    case_id: int | None,
    title: str = "Nouvelle conversation",
) -> AiConversation:
    conv = AiConversation(
        tenant_id=tenant_id,
        user_id=user_id,
        mode=mode,
        case_id=case_id,
        title=title,
    )
    db.add(conv)
    db.flush()
    return conv


def get_by_id(db: Session, conversation_id: int, tenant_id: int) -> AiConversation | None:
    return db.scalars(
        select(AiConversation).where(
            AiConversation.id == conversation_id,
            AiConversation.tenant_id == tenant_id,
            AiConversation.deleted_at.is_(None),
        )
    ).first()


def list_by_user(
    db: Session, tenant_id: int, user_id: int, limit: int = 30, offset: int = 0
) -> list[AiConversation]:
    return list(
        db.scalars(
            select(AiConversation)
            .where(
                AiConversation.tenant_id == tenant_id,
                AiConversation.user_id == user_id,
                AiConversation.deleted_at.is_(None),
            )
            .order_by(desc(AiConversation.updated_at))
            .limit(limit)
            .offset(offset)
        ).all()
    )


def add_message(
    db: Session,
    conversation: AiConversation,
    role: str,
    content: str,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
) -> AiMessage:
    msg = AiMessage(
        conversation_id=conversation.id,
        tenant_id=conversation.tenant_id,
        role=role,
        content=content,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )
    db.add(msg)
    # Touch updated_at on parent
    conversation.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.flush()
    return msg


def list_messages(
    db: Session, conversation_id: int, tenant_id: int
) -> list[AiMessage]:
    return list(
        db.scalars(
            select(AiMessage)
            .where(
                AiMessage.conversation_id == conversation_id,
                AiMessage.tenant_id == tenant_id,
            )
            .order_by(AiMessage.id)
        ).all()
    )


def update_title(db: Session, conversation: AiConversation, title: str) -> None:
    conversation.title = title[:200]
    conversation.updated_at = datetime.now(UTC).replace(tzinfo=None)


def soft_delete(db: Session, conversation_id: int, tenant_id: int) -> int:
    """Soft-delete une conversation. Retourne 1 si succes, 0 si introuvable."""
    result = db.execute(
        update(AiConversation)
        .where(
            AiConversation.id == conversation_id,
            AiConversation.tenant_id == tenant_id,
            AiConversation.deleted_at.is_(None),
        )
        .values(deleted_at=datetime.now(UTC).replace(tzinfo=None))
    )
    return result.rowcount
