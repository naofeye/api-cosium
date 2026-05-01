"""Partial unique index (tenant_id, cosium_id) WHERE cosium_id IS NOT NULL.

Codex review 2026-05-01 #6 : docs/BUSINESS_RULES.md et
docs/DATABASE_INDEXES.md annoncent `cosium_id UNIQUE par tenant`, mais la
migration y0z1a2b3c4d5 ne creait qu'un index non unique sur `cosium_id`. Des
doublons Cosium pouvaient donc etre inseres lors d'imports concurrents ou
de reprise partielle, en violation de l'invariant documente.

Cette migration ajoute l'index unique partiel pour verrouiller la regle au
niveau du schema. La condition `WHERE cosium_id IS NOT NULL` permet de
conserver plusieurs clients sans cosium_id dans le meme tenant (cas des
clients crees manuellement avant import Cosium).

ATTENTION : si la table contient deja des doublons (tenant_id, cosium_id),
la creation de l'index echouera. Verifier avec :

    SELECT tenant_id, cosium_id, COUNT(*)
    FROM customers
    WHERE cosium_id IS NOT NULL
    GROUP BY tenant_id, cosium_id
    HAVING COUNT(*) > 1;

Et nettoyer les doublons (merge ou suppression) avant d'appliquer.

Revision ID: f8i9j0k1l2m3
Revises: e8h9i0j1k2l3
Create Date: 2026-05-01 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


revision: str = "f8i9j0k1l2m3"
down_revision: Union[str, Sequence[str], None] = "e8h9i0j1k2l3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "uq_customers_tenant_cosium_id",
        "customers",
        ["tenant_id", "cosium_id"],
        unique=True,
        postgresql_where="cosium_id IS NOT NULL",
        sqlite_where="cosium_id IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_index("uq_customers_tenant_cosium_id", table_name="customers")
