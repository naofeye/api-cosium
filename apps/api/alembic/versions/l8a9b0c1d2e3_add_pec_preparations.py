"""Add pec_preparations and pec_preparation_documents tables.

Revision ID: l8a9b0c1d2e3
Revises: l7f8g9h0i1j2
Create Date: 2026-04-08 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "l8a9b0c1d2e3"
down_revision: str | None = "l7f8g9h0i1j2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pec_preparations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("devis_id", sa.Integer(), sa.ForeignKey("devis.id"), nullable=True),
        sa.Column("pec_request_id", sa.Integer(), sa.ForeignKey("pec_requests.id"), nullable=True),
        sa.Column("consolidated_data", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="en_preparation"),
        sa.Column("completude_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("errors_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warnings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("user_validations", sa.Text(), nullable=True),
        sa.Column("user_corrections", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pec_preparations_tenant_id", "pec_preparations", ["tenant_id"])
    op.create_index("ix_pec_preparations_customer_id", "pec_preparations", ["customer_id"])
    op.create_index("ix_pec_preparations_devis_id", "pec_preparations", ["devis_id"])
    op.create_index("ix_pec_preparations_pec_request_id", "pec_preparations", ["pec_request_id"])
    op.create_index("ix_pec_preparations_status", "pec_preparations", ["status"])
    op.create_index("ix_pec_prep_tenant_customer", "pec_preparations", ["tenant_id", "customer_id"])
    op.create_index("ix_pec_prep_tenant_status", "pec_preparations", ["tenant_id", "status"])

    op.create_table(
        "pec_preparation_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column(
            "preparation_id",
            sa.Integer(),
            sa.ForeignKey("pec_preparations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=True),
        sa.Column("cosium_document_id", sa.Integer(), nullable=True),
        sa.Column("document_role", sa.String(50), nullable=False, server_default="autre"),
        sa.Column(
            "extraction_id",
            sa.Integer(),
            sa.ForeignKey("document_extractions.id"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_pec_preparation_documents_preparation_id",
        "pec_preparation_documents",
        ["preparation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_pec_preparation_documents_preparation_id", "pec_preparation_documents")
    op.drop_table("pec_preparation_documents")
    op.drop_index("ix_pec_prep_tenant_status", "pec_preparations")
    op.drop_index("ix_pec_prep_tenant_customer", "pec_preparations")
    op.drop_index("ix_pec_preparations_status", "pec_preparations")
    op.drop_index("ix_pec_preparations_pec_request_id", "pec_preparations")
    op.drop_index("ix_pec_preparations_devis_id", "pec_preparations")
    op.drop_index("ix_pec_preparations_customer_id", "pec_preparations")
    op.drop_index("ix_pec_preparations_tenant_id", "pec_preparations")
    op.drop_table("pec_preparations")
