"""Add batch_operations and batch_operation_items tables

Revision ID: n9h0i1j2k3l4
Revises: m8g9h0i1j2k3
Create Date: 2026-04-05 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "n9h0i1j2k3l4"
down_revision: Union[str, None] = "m8g9h0i1j2k3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "batch_operations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False, server_default="optisante"),
        sa.Column("marketing_code", sa.String(255), nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="en_cours"),
        sa.Column("total_clients", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clients_prets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clients_incomplets", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clients_en_conflit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("clients_erreur", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_batch_operations_tenant_id", "batch_operations", ["tenant_id"])
    op.create_index("ix_batch_ops_tenant_status", "batch_operations", ["tenant_id", "status"])
    op.create_index("ix_batch_ops_tenant_code", "batch_operations", ["tenant_id", "marketing_code"])

    op.create_table(
        "batch_operation_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("batch_operations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="en_attente"),
        sa.Column("pec_preparation_id", sa.Integer(), sa.ForeignKey("pec_preparations.id"), nullable=True),
        sa.Column("completude_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("errors_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warnings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_batch_operation_items_batch_id", "batch_operation_items", ["batch_id"])
    op.create_index("ix_batch_operation_items_customer_id", "batch_operation_items", ["customer_id"])
    op.create_index("ix_batch_items_batch_status", "batch_operation_items", ["batch_id", "status"])


def downgrade() -> None:
    op.drop_table("batch_operation_items")
    op.drop_table("batch_operations")
