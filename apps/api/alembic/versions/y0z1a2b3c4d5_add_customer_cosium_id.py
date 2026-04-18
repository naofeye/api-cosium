"""Add missing cosium_id column to customers table.

Le modèle `Customer.cosium_id` (apps/api/app/models/client.py:14) existe depuis
longtemps, mais aucune migration Alembic ne l'ajoutait à la table `customers`.
Les tests backend passaient via SQLite + `create_all()` dans conftest, mais
les déploiements PostgreSQL frais (ex: E2E CI) plantaient au premier SELECT.

Cette migration ajoute la colonne + l'index (nullable, String(50)).

Revision ID: y0z1a2b3c4d5
Revises: x9y0z1a2b3c4
Create Date: 2026-04-18 13:45:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "y0z1a2b3c4d5"
down_revision: Union[str, Sequence[str], None] = "x9y0z1a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("cosium_id", sa.String(length=50), nullable=True),
    )
    op.create_index(
        "ix_customers_cosium_id",
        "customers",
        ["cosium_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_customers_cosium_id", table_name="customers")
    op.drop_column("customers", "cosium_id")
