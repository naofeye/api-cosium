"""Add original_facture_id + motif_avoir on factures (avoirs / notes de credit).

Justification :
- Norme comptable francaise : on ne SUPPRIME ni ne MODIFIE jamais une facture
  emise. Pour annuler ou rembourser, on emet un AVOIR (note de credit) avec
  des montants negatifs, lie a la facture originale.
- Cas d'usage : retour produit, erreur de facturation, geste commercial,
  remboursement partiel.
- L'avoir est une facture (meme table) avec :
  * `original_facture_id` -> facture corrigee
  * Montants negatifs (montant_ttc < 0)
  * Numerotation distincte (prefix "AVO-" suggested)

Revision ID: c6f7g8h9i0j1
Revises: b5e6f7g8h9i0
Create Date: 2026-04-29 04:55:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c6f7g8h9i0j1"
down_revision: str = "b5e6f7g8h9i0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "factures",
        sa.Column("original_facture_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "factures",
        sa.Column("motif_avoir", sa.String(length=500), nullable=True),
    )
    op.create_foreign_key(
        "fk_factures_original_facture_id",
        "factures",
        "factures",
        ["original_facture_id"],
        ["id"],
    )
    op.create_index("ix_factures_original_facture_id", "factures", ["original_facture_id"])


def downgrade() -> None:
    op.drop_index("ix_factures_original_facture_id", table_name="factures")
    op.drop_constraint("fk_factures_original_facture_id", "factures", type_="foreignkey")
    op.drop_column("factures", "motif_avoir")
    op.drop_column("factures", "original_facture_id")
