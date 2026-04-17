"""add totp_backup_codes_hash_json column to users

Revision ID: w8x9y0z1a2b3
Revises: v7w8x9y0z1a2
Create Date: 2026-04-17 18:15:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "w8x9y0z1a2b3"
down_revision = "v7w8x9y0z1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("totp_backup_codes_hash_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "totp_backup_codes_hash_json")
