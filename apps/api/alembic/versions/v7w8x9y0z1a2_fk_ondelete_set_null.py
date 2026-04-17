"""add ondelete=SET NULL on nullable FKs

Revision ID: v7w8x9y0z1a2
Revises: u6v7w8x9y0z1
Create Date: 2026-04-16 23:30:00.000000
"""
from alembic import op

revision = "v7w8x9y0z1a2"
down_revision = "u6v7w8x9y0z1"
branch_labels = None
depends_on = None


# (table, column, parent_table, parent_column)
# Note : cosium_third_party_payments n'a pas de colonne customer_id (liaison
# via invoice_cosium_id uniquement), donc absente de cette liste.
_SET_NULL_FKS = [
    ("cosium_documents", "customer_id", "customers", "id"),
    ("cosium_invoices", "customer_id", "customers", "id"),
    ("cosium_payments", "customer_id", "customers", "id"),
    ("cosium_customer_tags", "customer_id", "customers", "id"),
    ("documents", "document_type_id", "document_types", "id"),
    ("interactions", "created_by", "users", "id"),
]


def _fk_name(table: str, column: str) -> str:
    return f"{table}_{column}_fkey"


def upgrade() -> None:
    # DROP CONSTRAINT IF EXISTS (SQL brut) : un op.drop_constraint() qui echoue
    # aborte la transaction PostgreSQL en DDL transactionnel. IF EXISTS garantit
    # l'idempotence sans avoir a attraper l'exception.
    for table, column, parent_table, parent_column in _SET_NULL_FKS:
        fk_name = _fk_name(table, column)
        op.execute(f'ALTER TABLE "{table}" DROP CONSTRAINT IF EXISTS "{fk_name}"')
        op.create_foreign_key(
            fk_name,
            table,
            parent_table,
            [column],
            [parent_column],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    for table, column, parent_table, parent_column in _SET_NULL_FKS:
        fk_name = _fk_name(table, column)
        op.execute(f'ALTER TABLE "{table}" DROP CONSTRAINT IF EXISTS "{fk_name}"')
        op.create_foreign_key(
            fk_name,
            table,
            parent_table,
            [column],
            [parent_column],
        )
