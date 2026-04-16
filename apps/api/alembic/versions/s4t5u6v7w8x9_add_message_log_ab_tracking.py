"""add A/B tracking columns to message_logs

Revision ID: s4t5u6v7w8x9
Revises: r3s4t5u6v7w8
Create Date: 2026-04-16 00:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "s4t5u6v7w8x9"
down_revision = "r3s4t5u6v7w8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("message_logs", sa.Column("variant_key", sa.String(length=30), nullable=True))
    op.add_column("message_logs", sa.Column("opened_at", sa.DateTime(), nullable=True))
    op.add_column("message_logs", sa.Column("clicked_at", sa.DateTime(), nullable=True))
    op.add_column("message_logs", sa.Column("replied_at", sa.DateTime(), nullable=True))
    op.create_index("ix_message_logs_variant_key", "message_logs", ["variant_key"])


def downgrade() -> None:
    op.drop_index("ix_message_logs_variant_key", table_name="message_logs")
    op.drop_column("message_logs", "replied_at")
    op.drop_column("message_logs", "clicked_at")
    op.drop_column("message_logs", "opened_at")
    op.drop_column("message_logs", "variant_key")
