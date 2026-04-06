"""Add client_mutuelles table

Revision ID: j5d6e7f8g9h0
Revises: i4c5d6e7f8g9
Create Date: 2026-04-05 20:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "j5d6e7f8g9h0"
down_revision: Union[str, Sequence[str], None] = "i4c5d6e7f8g9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create client_mutuelles table."""
    op.create_table(
        "client_mutuelles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("mutuelle_id", sa.Integer(), nullable=True),
        sa.Column("mutuelle_name", sa.String(length=255), nullable=False),
        sa.Column("numero_adherent", sa.String(length=100), nullable=True),
        sa.Column("type_beneficiaire", sa.String(length=50), nullable=False, server_default="assure"),
        sa.Column("date_debut", sa.Date(), nullable=True),
        sa.Column("date_fin", sa.Date(), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False, server_default="cosium_tpp"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_client_mutuelles_tenant_id", "client_mutuelles", ["tenant_id"])
    op.create_index("ix_client_mutuelles_customer_id", "client_mutuelles", ["customer_id"])
    op.create_index(
        "ix_client_mutuelles_tenant_customer", "client_mutuelles", ["tenant_id", "customer_id"]
    )
    op.create_index(
        "ix_client_mutuelles_tenant_mutuelle", "client_mutuelles", ["tenant_id", "mutuelle_id"]
    )


def downgrade() -> None:
    """Drop client_mutuelles table."""
    op.drop_index("ix_client_mutuelles_tenant_mutuelle", table_name="client_mutuelles")
    op.drop_index("ix_client_mutuelles_tenant_customer", table_name="client_mutuelles")
    op.drop_index("ix_client_mutuelles_customer_id", table_name="client_mutuelles")
    op.drop_index("ix_client_mutuelles_tenant_id", table_name="client_mutuelles")
    op.drop_table("client_mutuelles")
