"""add_multi_tenant_tables

Revision ID: a1b2c3d4e5f6
Revises: c8405d5ebfc0
Create Date: 2026-04-04 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'c8405d5ebfc0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tables that need tenant_id
TENANT_TABLES = [
    "customers", "cases", "documents", "devis", "devis_lignes",
    "factures", "facture_lignes", "payments", "bank_transactions",
    "notifications", "action_items", "audit_logs",
    "pec_requests", "pec_status_history", "relances",
    "interactions", "segments", "segment_memberships",
    "campaigns", "message_logs", "marketing_consents",
    "payer_organizations", "payer_contracts",
    "reminder_plans", "reminders", "reminder_templates",
]

# Tables with dedicated composite index (tenant_id, id)
INDEX_TABLES = ["customers", "cases", "factures", "payments"]


def upgrade() -> None:
    # 1. Create organizations table
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("plan", sa.String(30), nullable=False, server_default="solo"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])

    # 2. Create tenants table
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("cosium_tenant", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])
    op.create_index("ix_tenants_organization_id", "tenants", ["organization_id"])

    # 3. Create tenant_users table
    op.create_table(
        "tenant_users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(30), nullable=False, server_default="operator"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.UniqueConstraint("user_id", "tenant_id", name="uq_tenant_users_user_tenant"),
    )
    op.create_index("ix_tenant_users_user_id", "tenant_users", ["user_id"])
    op.create_index("ix_tenant_users_tenant_id", "tenant_users", ["tenant_id"])

    # 4. Add tenant_id column (NULLABLE first) to all business tables
    for table in TENANT_TABLES:
        op.add_column(table, sa.Column("tenant_id", sa.Integer(), nullable=True))

    # 5. Create default organization and tenant, assign all existing data
    op.execute(
        "INSERT INTO organizations (name, slug, contact_email, plan) "
        "VALUES ('Organisation par défaut', 'default', 'admin@optiflow.com', 'solo')"
    )
    op.execute(
        "INSERT INTO tenants (organization_id, name, slug, cosium_tenant) "
        "SELECT id, 'Magasin principal', 'default', NULL FROM organizations WHERE slug = 'default'"
    )
    # Update all existing rows to use the default tenant
    for table in TENANT_TABLES:
        op.execute(
            f"UPDATE {table} SET tenant_id = (SELECT id FROM tenants WHERE slug = 'default')"
        )
    # Assign all existing users to the default tenant as admin
    op.execute(
        "INSERT INTO tenant_users (user_id, tenant_id, role) "
        "SELECT u.id, t.id, 'admin' FROM users u CROSS JOIN tenants t WHERE t.slug = 'default'"
    )

    # 6. Make tenant_id NOT NULL
    for table in TENANT_TABLES:
        op.alter_column(table, "tenant_id", nullable=False)

    # 7. Add foreign key constraints
    for table in TENANT_TABLES:
        op.create_foreign_key(
            f"fk_{table}_tenant_id", table, "tenants", ["tenant_id"], ["id"]
        )

    # 8. Add indexes
    for table in TENANT_TABLES:
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])


def downgrade() -> None:
    # Remove indexes and FK constraints, then columns
    for table in TENANT_TABLES:
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_constraint(f"fk_{table}_tenant_id", table, type_="foreignkey")
        op.drop_column(table, "tenant_id")

    op.drop_table("tenant_users")
    op.drop_table("tenants")
    op.drop_table("organizations")
