"""add_onboarding_fields

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-04 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Organization: trial_ends_at
    op.add_column("organizations", sa.Column("trial_ends_at", sa.DateTime(), nullable=True))

    # Tenant: cosium credentials + onboarding status
    op.add_column("tenants", sa.Column("cosium_login", sa.String(255), nullable=True))
    op.add_column("tenants", sa.Column("cosium_password_enc", sa.String(500), nullable=True))
    op.add_column("tenants", sa.Column("cosium_connected", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("tenants", sa.Column("first_sync_done", sa.Boolean(), nullable=False, server_default=sa.text("false")))


def downgrade() -> None:
    op.drop_column("tenants", "first_sync_done")
    op.drop_column("tenants", "cosium_connected")
    op.drop_column("tenants", "cosium_password_enc")
    op.drop_column("tenants", "cosium_login")
    op.drop_column("organizations", "trial_ends_at")
