"""Add webhook_subscriptions + webhook_deliveries tables.

Feature : webhooks HTTP sortants pour notifier des systemes tiers d'evenements
metier (client.created, facture.created, facture.avoir_created, devis.created).

Schema :
- webhook_subscriptions : 1 par tenant, URL + event_types JSON + secret HMAC
- webhook_deliveries : 1 ligne par tentative, status (pending/success/
  retrying/failed) + backoff via next_retry_at

Revision ID: b5c6d7e8f9a1
Revises: a4b5c6d7e8f9
Create Date: 2026-05-02 07:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "b5c6d7e8f9a1"
down_revision: Union[str, Sequence[str], None] = "a4b5c6d7e8f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("event_types", sa.JSON(), nullable=False),
        sa.Column("secret", sa.String(length=128), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_webhook_subscriptions_tenant_id",
        "webhook_subscriptions",
        ["tenant_id"],
    )
    op.create_index(
        "ix_webhook_subs_tenant_active",
        "webhook_subscriptions",
        ["tenant_id", "is_active"],
    )

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "attempts", sa.Integer(), nullable=False, server_default=sa.text("0")
        ),
        sa.Column("last_status_code", sa.Integer(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["webhook_subscriptions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_webhook_deliveries_subscription_id",
        "webhook_deliveries",
        ["subscription_id"],
    )
    op.create_index(
        "ix_webhook_deliveries_tenant_id",
        "webhook_deliveries",
        ["tenant_id"],
    )
    op.create_index(
        "ix_webhook_deliveries_event_type",
        "webhook_deliveries",
        ["event_type"],
    )
    op.create_index(
        "ix_webhook_deliveries_status",
        "webhook_deliveries",
        ["status"],
    )
    op.create_index(
        "ix_webhook_deliveries_created_at",
        "webhook_deliveries",
        ["created_at"],
    )
    op.create_index(
        "ix_webhook_deliv_tenant_created",
        "webhook_deliveries",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_webhook_deliv_status_next_retry",
        "webhook_deliveries",
        ["status", "next_retry_at"],
    )
    op.create_index(
        "ix_webhook_deliv_event_id",
        "webhook_deliveries",
        ["event_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_webhook_deliv_event_id", table_name="webhook_deliveries")
    op.drop_index(
        "ix_webhook_deliv_status_next_retry", table_name="webhook_deliveries"
    )
    op.drop_index(
        "ix_webhook_deliv_tenant_created", table_name="webhook_deliveries"
    )
    op.drop_index(
        "ix_webhook_deliveries_created_at", table_name="webhook_deliveries"
    )
    op.drop_index(
        "ix_webhook_deliveries_status", table_name="webhook_deliveries"
    )
    op.drop_index(
        "ix_webhook_deliveries_event_type", table_name="webhook_deliveries"
    )
    op.drop_index(
        "ix_webhook_deliveries_tenant_id", table_name="webhook_deliveries"
    )
    op.drop_index(
        "ix_webhook_deliveries_subscription_id", table_name="webhook_deliveries"
    )
    op.drop_table("webhook_deliveries")

    op.drop_index(
        "ix_webhook_subs_tenant_active", table_name="webhook_subscriptions"
    )
    op.drop_index(
        "ix_webhook_subscriptions_tenant_id", table_name="webhook_subscriptions"
    )
    op.drop_table("webhook_subscriptions")
