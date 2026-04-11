"""add_cosium_cookie_columns_to_tenants

Revision ID: 5ae5ee2cc95d
Revises: c81d2f00b30f
Create Date: 2026-04-05 02:22:39.163395

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5ae5ee2cc95d'
down_revision: Union[str, Sequence[str], None] = 'c81d2f00b30f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('tenants', sa.Column('cosium_cookie_access_token_enc', sa.String(length=1000), nullable=True))
    op.add_column('tenants', sa.Column('cosium_cookie_device_credential_enc', sa.String(length=1000), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tenants', 'cosium_cookie_device_credential_enc')
    op.drop_column('tenants', 'cosium_cookie_access_token_enc')
