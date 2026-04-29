"""Add ai_conversations + ai_messages tables (historique chat persistente).

- ai_conversations : 1 thread = (user_id, tenant_id, mode, optional case_id, title)
- ai_messages : N messages role=user/assistant/error, content texte

Revision ID: d7g8h9i0j1k2
Revises: c6f7g8h9i0j1
Create Date: 2026-04-29 05:15:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d7g8h9i0j1k2"
down_revision: str = "c6f7g8h9i0j1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_conversations",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False, server_default="Nouvelle conversation"),
        sa.Column("mode", sa.String(length=50), nullable=False, server_default="dossier"),
        sa.Column("case_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_conversations_tenant_id", "ai_conversations", ["tenant_id"])
    op.create_index("ix_ai_conversations_case_id", "ai_conversations", ["case_id"])
    op.create_index("ix_ai_conversations_deleted_at", "ai_conversations", ["deleted_at"])
    op.create_index(
        "ix_ai_conversations_tenant_user_updated",
        "ai_conversations",
        ["tenant_id", "user_id", "updated_at"],
    )

    op.create_table(
        "ai_messages",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["ai_conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_messages_tenant_id", "ai_messages", ["tenant_id"])
    op.create_index("ix_ai_messages_conversation_id", "ai_messages", ["conversation_id", "id"])


def downgrade() -> None:
    op.drop_index("ix_ai_messages_conversation_id", table_name="ai_messages")
    op.drop_index("ix_ai_messages_tenant_id", table_name="ai_messages")
    op.drop_table("ai_messages")
    op.drop_index("ix_ai_conversations_tenant_user_updated", table_name="ai_conversations")
    op.drop_index("ix_ai_conversations_deleted_at", table_name="ai_conversations")
    op.drop_index("ix_ai_conversations_case_id", table_name="ai_conversations")
    op.drop_index("ix_ai_conversations_tenant_id", table_name="ai_conversations")
    op.drop_table("ai_conversations")
