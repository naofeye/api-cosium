"""add soft_delete to Facture/Devis + composite indexes (audit phase 0.3)

Revision ID: q2r3s4t5u6v7
Revises: p1q2r3s4t5u6
Create Date: 2026-04-16 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "q2r3s4t5u6v7"
down_revision = "p1q2r3s4t5u6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Soft-delete Facture / Devis (harmonisation avec Customer.deleted_at)
    op.add_column("factures", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index("ix_factures_deleted_at", "factures", ["deleted_at"])

    op.add_column("devis", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index("ix_devis_deleted_at", "devis", ["deleted_at"])

    # Note : les indexes composites ix_documents_tenant_uploaded_at, ix_cases_tenant_status,
    # ix_payments_tenant_date_paiement sont deja crees par la migration a2b3c4d5e6f7.
    # Ils avaient ete ajoutes ici par erreur (doublon detecte en CI upgrade head).


def downgrade() -> None:
    op.drop_index("ix_devis_deleted_at", table_name="devis")
    op.drop_column("devis", "deleted_at")

    op.drop_index("ix_factures_deleted_at", table_name="factures")
    op.drop_column("factures", "deleted_at")
