"""add_composite_and_fk_indexes

Revision ID: a2b3c4d5e6f7
Revises: 6167ea1fa82a
Create Date: 2026-04-04 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "6167ea1fa82a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing FK indexes and composite tenant+status indexes."""
    # FK columns missing indexes
    op.create_index("ix_ai_usage_logs_user_id", "ai_usage_logs", ["user_id"])
    op.create_index("ix_documents_document_type_id", "documents", ["document_type_id"])
    op.create_index("ix_interactions_created_by", "interactions", ["created_by"])
    op.create_index("ix_relances_created_by", "relances", ["created_by"])
    op.create_index("ix_reminders_created_by", "reminders", ["created_by"])

    # Performance indexes for filtered queries
    op.create_index("ix_bank_transactions_date", "bank_transactions", ["date"])
    op.create_index("ix_bank_transactions_reconciled", "bank_transactions", ["reconciled"])

    # Composite indexes for tenant+status (used in dashboards/analytics)
    op.create_index("ix_cases_tenant_status", "cases", ["tenant_id", "status"])
    op.create_index("ix_factures_tenant_status", "factures", ["tenant_id", "status"])
    op.create_index("ix_devis_tenant_status", "devis", ["tenant_id", "status"])
    op.create_index("ix_payments_tenant_status", "payments", ["tenant_id", "status"])


def downgrade() -> None:
    """Remove composite and FK indexes."""
    op.drop_index("ix_payments_tenant_status", table_name="payments")
    op.drop_index("ix_devis_tenant_status", table_name="devis")
    op.drop_index("ix_factures_tenant_status", table_name="factures")
    op.drop_index("ix_cases_tenant_status", table_name="cases")
    op.drop_index("ix_bank_transactions_reconciled", table_name="bank_transactions")
    op.drop_index("ix_bank_transactions_date", table_name="bank_transactions")
    op.drop_index("ix_reminders_created_by", table_name="reminders")
    op.drop_index("ix_relances_created_by", table_name="relances")
    op.drop_index("ix_interactions_created_by", table_name="interactions")
    op.drop_index("ix_documents_document_type_id", table_name="documents")
    op.drop_index("ix_ai_usage_logs_user_id", table_name="ai_usage_logs")
