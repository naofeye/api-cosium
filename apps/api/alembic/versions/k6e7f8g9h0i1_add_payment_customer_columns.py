"""Add customer_cosium_id and customer_id to cosium_payments

Revision ID: k6e7f8g9h0i1
Revises: j5d6e7f8g9h0
Create Date: 2026-04-05 22:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "k6e7f8g9h0i1"
down_revision: Union[str, None] = "j5d6e7f8g9h0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("cosium_payments", sa.Column("customer_cosium_id", sa.String(50), nullable=True))
    op.add_column("cosium_payments", sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=True))
    op.create_index("ix_cosium_payments_customer_cosium_id", "cosium_payments", ["customer_cosium_id"])
    op.create_index("ix_cosium_payments_customer_id", "cosium_payments", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_cosium_payments_customer_id", table_name="cosium_payments")
    op.drop_index("ix_cosium_payments_customer_cosium_id", table_name="cosium_payments")
    op.drop_column("cosium_payments", "customer_id")
    op.drop_column("cosium_payments", "customer_cosium_id")
