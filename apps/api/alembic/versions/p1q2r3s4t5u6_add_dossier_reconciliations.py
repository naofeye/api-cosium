"""add dossier_reconciliations table

Revision ID: p1q2r3s4t5u6
Revises: o0p1q2r3s4t5
Create Date: 2026-04-15 00:08:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "p1q2r3s4t5u6"
down_revision = "o0p1q2r3s4t5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dossier_reconciliations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="en_attente"),
        sa.Column("confidence", sa.String(length=20), nullable=False, server_default="incertain"),
        sa.Column("total_facture", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_outstanding", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_paid", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_secu", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_mutuelle", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_client", sa.Float(), nullable=False, server_default="0"),
        sa.Column("total_avoir", sa.Float(), nullable=False, server_default="0"),
        sa.Column("invoice_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("payment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quote_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("credit_note_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("has_pec", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("pec_status", sa.String(length=50), nullable=True),
        sa.Column("detail_json", sa.Text(), nullable=True),
        sa.Column("anomalies", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("reconciled_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dossier_reconciliations_tenant_id", "dossier_reconciliations", ["tenant_id"])
    op.create_index("ix_dossier_reconciliations_customer_id", "dossier_reconciliations", ["customer_id"])
    op.create_index("ix_recon_tenant_customer", "dossier_reconciliations", ["tenant_id", "customer_id"], unique=True)
    op.create_index("ix_recon_tenant_status", "dossier_reconciliations", ["tenant_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_recon_tenant_status", table_name="dossier_reconciliations")
    op.drop_index("ix_recon_tenant_customer", table_name="dossier_reconciliations")
    op.drop_index("ix_dossier_reconciliations_customer_id", table_name="dossier_reconciliations")
    op.drop_index("ix_dossier_reconciliations_tenant_id", table_name="dossier_reconciliations")
    op.drop_table("dossier_reconciliations")
