"""add ON DELETE CASCADE on business FKs (audit phase 0.3)

Child → parent CASCADE uniquement (documents/devis/factures/payments/pec_requests → cases,
cases/client_mutuelles → customers). Les FK tenant_id restent RESTRICT (protection).

Revision ID: r3s4t5u6v7w8
Revises: q2r3s4t5u6v7
Create Date: 2026-04-16 00:10:00.000000
"""
from alembic import op

revision = "r3s4t5u6v7w8"
down_revision = "q2r3s4t5u6v7"
branch_labels = None
depends_on = None


# Liste des FK à migrer : (table enfant, colonne FK, table parent, ondelete)
CASCADE_FKS = [
    ("documents", "case_id", "cases", "CASCADE"),
    ("devis", "case_id", "cases", "CASCADE"),
    ("factures", "case_id", "cases", "CASCADE"),
    ("payments", "case_id", "cases", "CASCADE"),
    ("pec_requests", "case_id", "cases", "CASCADE"),
    ("interactions", "case_id", "cases", "CASCADE"),
    ("cases", "customer_id", "customers", "CASCADE"),
    ("client_mutuelles", "customer_id", "customers", "CASCADE"),
    ("payments", "facture_id", "factures", "SET NULL"),
]


def _fk_name(table: str, column: str) -> str:
    """Nom de contrainte par défaut généré par Alembic/Postgres."""
    return f"{table}_{column}_fkey"


def upgrade() -> None:
    for table, column, parent, ondelete in CASCADE_FKS:
        constraint_name = _fk_name(table, column)
        op.drop_constraint(constraint_name, table, type_="foreignkey")
        op.create_foreign_key(
            constraint_name,
            table,
            parent,
            [column],
            ["id"],
            ondelete=ondelete,
        )


def downgrade() -> None:
    for table, column, parent, _ondelete in CASCADE_FKS:
        constraint_name = _fk_name(table, column)
        op.drop_constraint(constraint_name, table, type_="foreignkey")
        op.create_foreign_key(
            constraint_name,
            table,
            parent,
            [column],
            ["id"],
        )
