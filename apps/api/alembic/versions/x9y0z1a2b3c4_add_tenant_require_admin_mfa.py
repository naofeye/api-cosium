"""add require_admin_mfa to tenants

Revision ID: x9y0z1a2b3c4
Revises: w8x9y0z1a2b3
Create Date: 2026-04-17 18:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "x9y0z1a2b3c4"
down_revision = "w8x9y0z1a2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # server_default="false" pour les lignes existantes (backfill), puis retire le default
    # cote SQLAlchemy (geré par le model default=False).
    op.add_column(
        "tenants",
        sa.Column(
            "require_admin_mfa",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    # Retirer le server_default pour ne pas polluer les futurs inserts purs Python
    op.alter_column("tenants", "require_admin_mfa", server_default=None)


def downgrade() -> None:
    op.drop_column("tenants", "require_admin_mfa")
