"""Security audit fixes: tenant isolation, composite unique constraints, indexes

- Add tenant_id to BatchOperationItem and PecPreparationDocument
- Change Devis.numero, Facture.numero, PayerOrganization.code from globally unique to per-tenant unique
- Change Payment.idempotency_key from globally unique to per-tenant unique
- Add composite indexes for (tenant_id, status) on payments and factures

Revision ID: o0p1q2r3s4t5
Revises: n9h0i1j2k3l4
Create Date: 2026-04-07 12:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "o0p1q2r3s4t5"
down_revision: Union[str, None] = "n9h0i1j2k3l4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_index(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _create_index_if_missing(name: str, table_name: str, columns: list[str], *, unique: bool = False) -> None:
    if not _has_index(table_name, name):
        op.create_index(name, table_name, columns, unique=unique)


def upgrade() -> None:
    # --- BatchOperationItem: add tenant_id ---
    op.add_column("batch_operation_items", sa.Column("tenant_id", sa.Integer(), nullable=True))
    # Backfill from parent batch_operations
    op.execute("""
        UPDATE batch_operation_items boi
        SET tenant_id = bo.tenant_id
        FROM batch_operations bo
        WHERE boi.batch_id = bo.id AND boi.tenant_id IS NULL
    """)
    op.alter_column("batch_operation_items", "tenant_id", nullable=False)
    op.create_foreign_key("fk_batch_items_tenant", "batch_operation_items", "tenants", ["tenant_id"], ["id"])
    op.create_index("ix_batch_items_tenant_id", "batch_operation_items", ["tenant_id"])

    # --- PecPreparationDocument: add tenant_id ---
    op.add_column("pec_preparation_documents", sa.Column("tenant_id", sa.Integer(), nullable=True))
    # Backfill from parent pec_preparations
    op.execute("""
        UPDATE pec_preparation_documents ppd
        SET tenant_id = pp.tenant_id
        FROM pec_preparations pp
        WHERE ppd.preparation_id = pp.id AND ppd.tenant_id IS NULL
    """)
    op.alter_column("pec_preparation_documents", "tenant_id", nullable=False)
    op.create_foreign_key("fk_pec_prep_docs_tenant", "pec_preparation_documents", "tenants", ["tenant_id"], ["id"])
    op.create_index("ix_pec_prep_docs_tenant_id", "pec_preparation_documents", ["tenant_id"])

    # --- Devis.numero: global unique -> per-tenant unique ---
    op.drop_constraint("devis_numero_key", "devis", type_="unique")
    _create_index_if_missing("ix_devis_tenant_numero", "devis", ["tenant_id", "numero"], unique=True)

    # --- Facture.numero: global unique -> per-tenant unique ---
    op.drop_constraint("factures_numero_key", "factures", type_="unique")
    _create_index_if_missing("ix_factures_tenant_numero", "factures", ["tenant_id", "numero"], unique=True)
    _create_index_if_missing("ix_factures_tenant_status", "factures", ["tenant_id", "status"])

    # --- PayerOrganization.code: global unique -> per-tenant unique ---
    op.drop_constraint("payer_organizations_code_key", "payer_organizations", type_="unique")
    _create_index_if_missing("ix_payer_orgs_tenant_code", "payer_organizations", ["tenant_id", "code"], unique=True)

    # --- Payment.idempotency_key: global unique -> per-tenant unique ---
    op.drop_constraint("payments_idempotency_key_key", "payments", type_="unique")
    _create_index_if_missing("ix_payments_tenant_idempotency", "payments", ["tenant_id", "idempotency_key"], unique=True)
    _create_index_if_missing("ix_payments_tenant_status", "payments", ["tenant_id", "status"])


def downgrade() -> None:
    # Reverse indexes
    op.drop_index("ix_payments_tenant_status", "payments")
    op.drop_index("ix_payments_tenant_idempotency", "payments")
    op.create_unique_constraint("payments_idempotency_key_key", "payments", ["idempotency_key"])

    op.drop_index("ix_payer_orgs_tenant_code", "payer_organizations")
    op.create_unique_constraint("payer_organizations_code_key", "payer_organizations", ["code"])

    op.drop_index("ix_factures_tenant_status", "factures")
    op.drop_index("ix_factures_tenant_numero", "factures")
    op.create_unique_constraint("factures_numero_key", "factures", ["numero"])

    op.drop_index("ix_devis_tenant_numero", "devis")
    op.create_unique_constraint("devis_numero_key", "devis", ["numero"])

    # Remove tenant_id columns
    op.drop_index("ix_pec_prep_docs_tenant_id", "pec_preparation_documents")
    op.drop_constraint("fk_pec_prep_docs_tenant", "pec_preparation_documents", type_="foreignkey")
    op.drop_column("pec_preparation_documents", "tenant_id")

    op.drop_index("ix_batch_items_tenant_id", "batch_operation_items")
    op.drop_constraint("fk_batch_items_tenant", "batch_operation_items", type_="foreignkey")
    op.drop_column("batch_operation_items", "tenant_id")
