"""Add valid_until column on devis (expiration date).

Justification :
- Norme metier opticien : devis valide 90 jours par defaut.
- Permet a une task Celery de marquer automatiquement les devis expires
  (status="brouillon"|"envoye" ET valid_until < now()) → status="expire".
- Backfill des devis existants : created_at + 90 jours pour les non-archives.

Revision ID: b5e6f7g8h9i0
Revises: a4d5e6f7g8h9
Create Date: 2026-04-29 04:45:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b5e6f7g8h9i0"
down_revision: str = "a4d5e6f7g8h9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Add column nullable
    op.add_column(
        "devis",
        sa.Column("valid_until", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_devis_valid_until", "devis", ["valid_until"])

    # Backfill : created_at + 90 jours pour les devis non encore signes/archives
    # (status in 'brouillon', 'envoye'). Les autres restent NULL.
    conn.execute(
        sa.text(
            """
            UPDATE devis
            SET valid_until = created_at + INTERVAL '90 days'
            WHERE status IN ('brouillon', 'envoye')
              AND deleted_at IS NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_devis_valid_until", table_name="devis")
    op.drop_column("devis", "valid_until")
