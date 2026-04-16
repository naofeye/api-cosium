"""add cosium_invoiced_items table

Revision ID: t5u6v7w8x9y0
Revises: s4t5u6v7w8x9
Create Date: 2026-04-16 00:45:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "t5u6v7w8x9y0"
down_revision = "s4t5u6v7w8x9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cosium_invoiced_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("cosium_id", sa.Integer(), nullable=False),
        sa.Column("invoice_cosium_id", sa.Integer(), nullable=False),
        sa.Column("product_cosium_id", sa.String(length=50), nullable=True),
        sa.Column("product_label", sa.String(length=500), server_default="", nullable=False),
        sa.Column("product_family", sa.String(length=100), server_default="", nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("unit_price_ti", sa.Float(), server_default="0", nullable=False),
        sa.Column("total_ti", sa.Float(), server_default="0", nullable=False),
        sa.Column("synced_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cosium_invoiced_items_tenant_id", "cosium_invoiced_items", ["tenant_id"])
    op.create_index("ix_cosium_invoiced_items_cosium_id", "cosium_invoiced_items", ["cosium_id"])
    op.create_index("ix_cosium_invoiced_items_invoice_cosium_id", "cosium_invoiced_items", ["invoice_cosium_id"])
    op.create_index("ix_cosium_invoiced_items_product_cosium_id", "cosium_invoiced_items", ["product_cosium_id"])
    op.create_index(
        "ix_cosium_invoiced_items_tenant_cosium",
        "cosium_invoiced_items",
        ["tenant_id", "cosium_id"],
        unique=True,
    )
    op.create_index(
        "ix_cosium_invoiced_items_tenant_invoice",
        "cosium_invoiced_items",
        ["tenant_id", "invoice_cosium_id"],
    )
    op.create_index(
        "ix_cosium_invoiced_items_tenant_family",
        "cosium_invoiced_items",
        ["tenant_id", "product_family"],
    )


def downgrade() -> None:
    op.drop_index("ix_cosium_invoiced_items_tenant_family", table_name="cosium_invoiced_items")
    op.drop_index("ix_cosium_invoiced_items_tenant_invoice", table_name="cosium_invoiced_items")
    op.drop_index("ix_cosium_invoiced_items_tenant_cosium", table_name="cosium_invoiced_items")
    op.drop_index("ix_cosium_invoiced_items_product_cosium_id", table_name="cosium_invoiced_items")
    op.drop_index("ix_cosium_invoiced_items_invoice_cosium_id", table_name="cosium_invoiced_items")
    op.drop_index("ix_cosium_invoiced_items_cosium_id", table_name="cosium_invoiced_items")
    op.drop_index("ix_cosium_invoiced_items_tenant_id", table_name="cosium_invoiced_items")
    op.drop_table("cosium_invoiced_items")
