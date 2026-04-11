"""add_erp_abstraction

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-04-04 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tenant: erp_type + erp_config
    op.add_column("tenants", sa.Column("erp_type", sa.String(30), nullable=False, server_default="cosium"))
    op.add_column("tenants", sa.Column("erp_config", sa.JSON(), nullable=True))

    # Table tenant_erp_credentials
    op.create_table(
        "tenant_erp_credentials",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("erp_type", sa.String(30), nullable=False, server_default="cosium"),
        sa.Column("login", sa.String(255), nullable=True),
        sa.Column("password_encrypted", sa.String(500), nullable=True),
        sa.Column("base_url", sa.String(500), nullable=True),
        sa.Column("extra_config", sa.JSON(), nullable=True),
        sa.Column("last_sync_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "erp_type", name="uq_tenant_erp_creds"),
    )


def downgrade() -> None:
    op.drop_table("tenant_erp_credentials")
    op.drop_column("tenants", "erp_config")
    op.drop_column("tenants", "erp_type")
