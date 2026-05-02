"""Add tenant_id to refresh_tokens for tenant-aware refresh.

Audit Codex 2026-05-02 finding M2 : `auth_service.refresh()` regenerait les
tokens sur `tenants[0]` plutot que sur le tenant choisi via `switch_tenant()`.
Un user multi-tenant pouvait etre rebascule silencieusement sur un autre
tenant apres renouvellement de session.

Solution : stocker `tenant_id` dans la session refresh. Les anciens tokens
(NULL) tombent en fallback `tenants[0]` lors du prochain refresh.

Revision ID: a4b5c6d7e8f9
Revises: a4d5e6f7g8h9, f8i9j0k1l2m3
Create Date: 2026-05-02 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a4b5c6d7e8f9"
# Merge des 2 heads pre-existantes (audit_logs composite + cosium_id partial unique).
down_revision: tuple[str, ...] = ("a4d5e6f7g8h9", "f8i9j0k1l2m3")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "refresh_tokens",
        sa.Column("tenant_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_refresh_tokens_tenant_id",
        "refresh_tokens",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_refresh_tokens_tenant_id",
        "refresh_tokens",
        ["tenant_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_tenant_id", table_name="refresh_tokens")
    op.drop_constraint("fk_refresh_tokens_tenant_id", "refresh_tokens", type_="foreignkey")
    op.drop_column("refresh_tokens", "tenant_id")
