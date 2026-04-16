"""add TOTP columns to users (MFA)

Revision ID: u6v7w8x9y0z1
Revises: t5u6v7w8x9y0
Create Date: 2026-04-16 23:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "u6v7w8x9y0z1"
down_revision = "t5u6v7w8x9y0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_secret_enc", sa.String(length=255), nullable=True))
    op.add_column(
        "users",
        sa.Column("totp_enabled", sa.Boolean(), server_default="0", nullable=False),
    )
    op.add_column("users", sa.Column("totp_last_used_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "totp_last_used_at")
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret_enc")
