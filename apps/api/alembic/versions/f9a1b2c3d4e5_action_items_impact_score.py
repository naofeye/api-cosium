"""Add impact_score to action_items for financial-aware prioritization.

Permet de trier les action items par impact financier reel (montant facture
en retard, valeur client, urgence) plutot que par priorite categorielle
high/medium/low. Algorithme deterministe (pas d'API IA), calcule au
moment de la generation des items.

Score = base_priority (0-100) + montant_factor (0-200) + recency_factor (0-50)
- priority critical -> 100, high -> 70, medium -> 40, low -> 10
- montant : log10(montant_eur) * 50, max 200
- recency : 50 si <7j, 30 si <30j, 10 si <90j, 0 sinon

Revision ID: f9a1b2c3d4e5
Revises: e8f9a1b2c3d4
Create Date: 2026-05-03 12:30:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f9a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "e8f9a1b2c3d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "action_items",
        sa.Column(
            "impact_score",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    # Index pour le tri descendant
    op.create_index(
        "ix_action_items_tenant_user_score",
        "action_items",
        ["tenant_id", "user_id", "impact_score"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_action_items_tenant_user_score", table_name="action_items"
    )
    op.drop_column("action_items", "impact_score")
