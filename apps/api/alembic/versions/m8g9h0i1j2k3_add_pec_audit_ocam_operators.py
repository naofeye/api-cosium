"""Add pec_audit_entries, ocam_operators tables and ocam_operator_id column

Revision ID: m8g9h0i1j2k3
Revises: l7f8g9h0i1j2
Create Date: 2026-04-07 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "m8g9h0i1j2k3"
down_revision: Union[str, None] = "l8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- ocam_operators ---
    op.create_table(
        "ocam_operators",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=True),
        sa.Column("portal_url", sa.String(500), nullable=True),
        sa.Column("required_fields", sa.Text(), nullable=True),
        sa.Column("required_documents", sa.Text(), nullable=True),
        sa.Column("specific_rules", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ocam_operator_tenant", "ocam_operators", ["tenant_id"])
    op.create_index("ix_ocam_operator_code", "ocam_operators", ["tenant_id", "code"])

    # --- pec_audit_entries ---
    op.create_table(
        "pec_audit_entries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column(
            "preparation_id",
            sa.Integer(),
            sa.ForeignKey("pec_preparations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("field_name", sa.String(100), nullable=True),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pec_audit_tenant", "pec_audit_entries", ["tenant_id"])
    op.create_index("ix_pec_audit_preparation", "pec_audit_entries", ["preparation_id"])
    op.create_index("ix_pec_audit_created", "pec_audit_entries", ["created_at"])

    # --- Add ocam_operator_id to pec_preparations ---
    op.add_column(
        "pec_preparations",
        sa.Column("ocam_operator_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_pec_prep_ocam_operator",
        "pec_preparations",
        "ocam_operators",
        ["ocam_operator_id"],
        ["id"],
    )
    op.create_index(
        "ix_pec_prep_ocam_operator",
        "pec_preparations",
        ["ocam_operator_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_pec_prep_ocam_operator", table_name="pec_preparations")
    op.drop_constraint("fk_pec_prep_ocam_operator", "pec_preparations", type_="foreignkey")
    op.drop_column("pec_preparations", "ocam_operator_id")
    op.drop_table("pec_audit_entries")
    op.drop_table("ocam_operators")
