"""Add customer metadata columns (customer_number, optician, ophthalmologist, etc.)

Revision ID: i4c5d6e7f8g9
Revises: h3b4c5d6e7f8
Create Date: 2026-04-05 18:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "i4c5d6e7f8g9"
down_revision: Union[str, Sequence[str], None] = "h3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add missing Cosium metadata columns to customers table."""
    op.add_column(
        "customers",
        sa.Column("customer_number", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column("optician_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column("ophthalmologist_id", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column("street_number", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column("street_name", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column("mobile_phone_country", sa.String(length=10), nullable=True),
    )
    op.add_column(
        "customers",
        sa.Column("site_id", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    """Remove customer metadata columns."""
    op.drop_column("customers", "site_id")
    op.drop_column("customers", "mobile_phone_country")
    op.drop_column("customers", "street_name")
    op.drop_column("customers", "street_number")
    op.drop_column("customers", "ophthalmologist_id")
    op.drop_column("customers", "optician_name")
    op.drop_column("customers", "customer_number")
