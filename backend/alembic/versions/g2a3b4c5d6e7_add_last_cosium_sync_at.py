"""add_last_cosium_sync_at to tenants

Revision ID: g2a3b4c5d6e7
Revises: f1a2b3c4d5e6
Create Date: 2026-04-04 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g2a3b4c5d6e7'
down_revision: Union[str, Sequence[str], None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add last_cosium_sync_at column to tenants table."""
    op.add_column('tenants', sa.Column('last_cosium_sync_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove last_cosium_sync_at column from tenants table."""
    op.drop_column('tenants', 'last_cosium_sync_at')
