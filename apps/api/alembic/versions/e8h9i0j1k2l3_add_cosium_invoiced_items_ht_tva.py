"""Add HT/TVA/discount columns on cosium_invoiced_items.

La doc officielle Cosium (Invoiced Items API.pdf) expose plus que TTC :
- unitPriceExcludingTaxes (HT)
- totalPriceExcludingTaxes (HT)
- vatPercentage
- discount + discountType (PERCENTAGE | CURRENCY)
- rank (ordre dans la facture)

Avant cette migration on perdait toute l'info HT au sync, indispensable
pour les exports FEC/Sage (compta francaise normalisee qui exige HT par
ligne).

Revision ID: e8h9i0j1k2l3
Revises: d7g8h9i0j1k2
Create Date: 2026-04-29 11:05:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e8h9i0j1k2l3"
down_revision: str = "d7g8h9i0j1k2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cosium_invoiced_items", sa.Column("unit_price_te", sa.Float(), nullable=False, server_default="0"))
    op.add_column("cosium_invoiced_items", sa.Column("total_te", sa.Float(), nullable=False, server_default="0"))
    op.add_column("cosium_invoiced_items", sa.Column("vat_percentage", sa.Float(), nullable=False, server_default="0"))
    op.add_column("cosium_invoiced_items", sa.Column("discount", sa.Float(), nullable=False, server_default="0"))
    op.add_column("cosium_invoiced_items", sa.Column("discount_type", sa.String(length=20), nullable=True))
    op.add_column("cosium_invoiced_items", sa.Column("rank", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("cosium_invoiced_items", "rank")
    op.drop_column("cosium_invoiced_items", "discount_type")
    op.drop_column("cosium_invoiced_items", "discount")
    op.drop_column("cosium_invoiced_items", "vat_percentage")
    op.drop_column("cosium_invoiced_items", "total_te")
    op.drop_column("cosium_invoiced_items", "unit_price_te")
