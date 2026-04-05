"""add_client_avatar_url

Revision ID: f1a2b3c4d5e6
Revises: e8b0aa6788b4
Create Date: 2026-04-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e8b0aa6788b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add avatar_url column to customers table."""
    op.add_column('customers', sa.Column('avatar_url', sa.String(500), nullable=True))


def downgrade() -> None:
    """Remove avatar_url column from customers table."""
    op.drop_column('customers', 'avatar_url')
