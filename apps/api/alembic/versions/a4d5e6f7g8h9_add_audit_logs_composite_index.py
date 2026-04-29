"""Add composite index on audit_logs (tenant_id, created_at, action).

Justification :
- Les requetes audit les plus frequentes filtrent par tenant_id ET tranche
  temporelle (created_at), souvent + filtre action ('create', 'update', 'delete').
- L'index simple sur tenant_id seul force un index scan + filter sur le reste.
- Avec un index composite (tenant_id, created_at DESC, action), Postgres peut
  servir les pages "audit recent" + "audit par type d'action" sans tri secondaire.

Pattern de query cible :
  SELECT * FROM audit_logs
  WHERE tenant_id = :tid
    AND created_at >= :since
    [AND action IN ('create', 'update', 'delete')]
  ORDER BY created_at DESC LIMIT 50;

Revision ID: a4d5e6f7g8h9
Revises: z3c4d5e6f7g8
Create Date: 2026-04-29 04:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a4d5e6f7g8h9"
down_revision: str = "z3c4d5e6f7g8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if not conn.execute(
        sa.text("SELECT 1 FROM pg_indexes WHERE indexname = :idx"),
        {"idx": "ix_audit_logs_tenant_created_action"},
    ).scalar():
        op.create_index(
            "ix_audit_logs_tenant_created_action",
            "audit_logs",
            ["tenant_id", sa.text("created_at DESC"), "action"],
        )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_tenant_created_action", table_name="audit_logs")
