"""Add missing indexes on ForeignKey columns for JOIN performance.

6 FK columns identified without dedicated indexes:
- ai_usages.user_id, cosium_invoices.customer_id, documents.document_type_id,
  interactions.created_by, pec_status_history.created_by, reminders.created_by

Revision ID: z3c4d5e6f7g8
Revises: z2b3c4d5e6f7
Create Date: 2026-04-20 20:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "z3c4d5e6f7g8"
down_revision: str = "z2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INDEXES = [
    ("ix_ai_usage_logs_user_id", "ai_usage_logs", ["user_id"]),
    ("ix_cosium_invoices_customer_id", "cosium_invoices", ["customer_id"]),
    ("ix_documents_document_type_id", "documents", ["document_type_id"]),
    ("ix_interactions_created_by", "interactions", ["created_by"]),
    ("ix_pec_status_history_created_by", "pec_status_history", ["created_by"]),
    ("ix_reminders_created_by", "reminders", ["created_by"]),
]


def upgrade() -> None:
    for name, table, cols in _INDEXES:
        op.create_index(name, table, cols)


def downgrade() -> None:
    for name, table, _cols in reversed(_INDEXES):
        op.drop_index(name, table_name=table)
