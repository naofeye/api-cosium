"""Tests pour l'historique conversationnel du copilote IA."""

from unittest.mock import MagicMock, patch

import pytest

from app.repositories import ai_conversation_repo


@patch("app.services._ai.conversation.claude_provider")
def test_append_message_creates_conversation_when_id_none(mock_provider, db, default_tenant, seed_user):
    from app.services._ai.conversation import append_message

    mock_provider.query_with_usage.return_value = {
        "text": "Reponse IA",
        "tokens_in": 10,
        "tokens_out": 20,
        "model": "claude-haiku",
    }

    conv_id, answer = append_message(
        db,
        tenant_id=default_tenant.id,
        user_id=seed_user.id,
        question="Bonjour, dis-moi tout sur ce dossier",
        conversation_id=None,
        mode="dossier",
        case_id=None,
    )

    assert conv_id > 0
    assert answer == "Reponse IA"

    conv = ai_conversation_repo.get_by_id(db, conv_id, default_tenant.id)
    assert conv is not None
    assert conv.user_id == seed_user.id
    assert conv.title == "Bonjour, dis-moi tout sur ce dossier"
    assert conv.mode == "dossier"

    messages = ai_conversation_repo.list_messages(db, conv_id, default_tenant.id)
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Bonjour, dis-moi tout sur ce dossier"
    assert messages[1].role == "assistant"
    assert messages[1].content == "Reponse IA"
    assert messages[1].tokens_in == 10
    assert messages[1].tokens_out == 20


@patch("app.services._ai.conversation.claude_provider")
def test_append_message_replays_history(mock_provider, db, default_tenant, seed_user):
    """Lors de l'ajout d'une question dans une conv existante, l'historique
    doit etre passe au provider (le 2eme appel a query_with_usage doit
    contenir l'historique du 1er Q/R)."""
    from app.services._ai.conversation import append_message

    mock_provider.query_with_usage.return_value = {
        "text": "R1", "tokens_in": 5, "tokens_out": 5, "model": "m",
    }

    conv_id, _ = append_message(
        db, tenant_id=default_tenant.id, user_id=seed_user.id,
        question="Q1", conversation_id=None, mode="dossier", case_id=None,
    )

    mock_provider.query_with_usage.return_value = {
        "text": "R2", "tokens_in": 8, "tokens_out": 8, "model": "m",
    }
    append_message(
        db, tenant_id=default_tenant.id, user_id=seed_user.id,
        question="Q2", conversation_id=conv_id, mode="dossier", case_id=None,
    )

    # 2eme appel : history doit contenir Q1 + R1
    second_call_kwargs = mock_provider.query_with_usage.call_args_list[1].kwargs
    history = second_call_kwargs.get("history") or []
    assert len(history) == 2
    assert history[0] == {"role": "user", "content": "Q1"}
    assert history[1] == {"role": "assistant", "content": "R1"}


@patch("app.services._ai.conversation.claude_provider")
def test_append_message_logs_error_message_on_failure(mock_provider, db, default_tenant, seed_user):
    from app.services._ai.conversation import append_message

    mock_provider.query_with_usage.side_effect = RuntimeError("API down")

    with pytest.raises(RuntimeError):
        append_message(
            db, tenant_id=default_tenant.id, user_id=seed_user.id,
            question="Q ko", conversation_id=None, mode="dossier", case_id=None,
        )

    # La conversation a ete creee + message user sauve + message error sauve
    convs = ai_conversation_repo.list_by_user(db, default_tenant.id, seed_user.id)
    assert len(convs) == 1
    messages = ai_conversation_repo.list_messages(db, convs[0].id, default_tenant.id)
    roles = [m.role for m in messages]
    assert "user" in roles
    assert "error" in roles


@patch("app.services._ai.conversation.claude_provider")
def test_list_conversations_returns_user_only(mock_provider, db, default_tenant, seed_user):
    """List retourne uniquement les conversations de l'utilisateur courant."""
    from app.services._ai.conversation import append_message
    from app.models import User
    from app.security import hash_password

    mock_provider.query_with_usage.return_value = {
        "text": "R", "tokens_in": 0, "tokens_out": 0, "model": "m",
    }

    # User #1 (seed_user)
    append_message(
        db, tenant_id=default_tenant.id, user_id=seed_user.id,
        question="user1 q", conversation_id=None, mode="dossier", case_id=None,
    )

    # User #2
    user2 = User(email="other@test.com", password_hash=hash_password("X"), role="admin", is_active=True)
    db.add(user2)
    db.commit()
    append_message(
        db, tenant_id=default_tenant.id, user_id=user2.id,
        question="user2 q", conversation_id=None, mode="dossier", case_id=None,
    )

    convs1 = ai_conversation_repo.list_by_user(db, default_tenant.id, seed_user.id)
    convs2 = ai_conversation_repo.list_by_user(db, default_tenant.id, user2.id)
    assert len(convs1) == 1
    assert len(convs2) == 1
    assert convs1[0].id != convs2[0].id


def test_soft_delete_hides_from_list(db, default_tenant, seed_user):
    conv = ai_conversation_repo.create(db, default_tenant.id, seed_user.id, "dossier", None)
    db.commit()
    assert len(ai_conversation_repo.list_by_user(db, default_tenant.id, seed_user.id)) == 1
    ai_conversation_repo.soft_delete(db, conv.id, default_tenant.id)
    db.commit()
    assert len(ai_conversation_repo.list_by_user(db, default_tenant.id, seed_user.id)) == 0
    # Mais on peut encore retrouver via get_by_id ? Non — get_by_id filtre deleted_at IS NULL
    assert ai_conversation_repo.get_by_id(db, conv.id, default_tenant.id) is None
