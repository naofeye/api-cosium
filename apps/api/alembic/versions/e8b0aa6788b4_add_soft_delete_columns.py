"""add_soft_delete_columns

Revision ID: e8b0aa6788b4
Revises: a2b3c4d5e6f7
Create Date: 2026-04-04 23:38:33.629112

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8b0aa6788b4'
down_revision: Union[str, Sequence[str], None] = 'a2b3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('cases', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('customers', sa.Column('deleted_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('customers', 'deleted_at')
    op.drop_column('cases', 'deleted_at')
