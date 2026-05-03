"""Add api_tokens table for public REST API v1.

Feature : API publique read-only pour integrations partenaires (mutuelles,
plateformes tiers payant, outils comptables). Tokens scopes par tenant,
hashes SHA-256 (jamais stockes en clair).

Schema :
- name, prefix (4 chars affichables), hashed_token (sha256 hex)
- scopes JSON whitelist (read:clients, read:devis, etc.)
- expires_at, revoked, last_used_at pour audit
- created_by_user_id pour traceability

Revision ID: d7e8f9a1b2c3
Revises: c6d7e8f9a1b2
Create Date: 2026-05-03 10:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "d7e8f9a1b2c3"
down_revision: Union[str, Sequence[str], None] = "c6d7e8f9a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("prefix", sa.String(length=12), nullable=False),
        sa.Column("hashed_token", sa.String(length=64), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column(
            "revoked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_api_tokens_tenant_id", "api_tokens", ["tenant_id"]
    )
    op.create_index(
        "ix_api_tokens_hashed_token",
        "api_tokens",
        ["hashed_token"],
        unique=True,
    )
    op.create_index(
        "ix_api_tokens_tenant_revoked",
        "api_tokens",
        ["tenant_id", "revoked"],
    )


def downgrade() -> None:
    op.drop_index("ix_api_tokens_tenant_revoked", table_name="api_tokens")
    op.drop_index("ix_api_tokens_hashed_token", table_name="api_tokens")
    op.drop_index("ix_api_tokens_tenant_id", table_name="api_tokens")
    op.drop_table("api_tokens")
