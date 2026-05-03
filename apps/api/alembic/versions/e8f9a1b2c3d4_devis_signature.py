"""Add electronic signature fields to devis (eIDAS Simple).

Pour engagement client digital sans recourir a la signature manuscrite. V1
implemente la "Signature Electronique Simple" eIDAS : capture IP +
User-Agent + texte de consentement + horodatage. Suffisant legalement en
France pour les contrats < 1500 EUR (norme opticien : devis lunettes
courantes).

Champs :
- public_token : UUID v4 stocke en cleair, sert d'URL publique sans login
  (le client recoit le lien par email). Genere a l'envoi.
- signed_at : datetime de la signature
- signature_method : "clickwrap" (V1), futur "drawn", "tablet"
- signature_ip / signature_user_agent : audit trail
- signature_consent_text : texte exact accepte (preuve eIDAS)

Revision ID: e8f9a1b2c3d4
Revises: d7e8f9a1b2c3
Create Date: 2026-05-03 11:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "e8f9a1b2c3d4"
down_revision: Union[str, Sequence[str], None] = "d7e8f9a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "devis",
        sa.Column("public_token", sa.String(length=64), nullable=True),
    )
    op.add_column("devis", sa.Column("signed_at", sa.DateTime(), nullable=True))
    op.add_column(
        "devis",
        sa.Column("signature_method", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "devis", sa.Column("signature_ip", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "devis", sa.Column("signature_user_agent", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "devis", sa.Column("signature_consent_text", sa.Text(), nullable=True)
    )
    op.create_index(
        "ix_devis_public_token",
        "devis",
        ["public_token"],
        unique=True,
        postgresql_where=sa.text("public_token IS NOT NULL"),
        sqlite_where=sa.text("public_token IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_devis_public_token", table_name="devis")
    op.drop_column("devis", "signature_consent_text")
    op.drop_column("devis", "signature_user_agent")
    op.drop_column("devis", "signature_ip")
    op.drop_column("devis", "signature_method")
    op.drop_column("devis", "signed_at")
    op.drop_column("devis", "public_token")
