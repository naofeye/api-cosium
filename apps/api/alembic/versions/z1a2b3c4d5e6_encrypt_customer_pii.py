"""Encrypt Customer PII fields (Tier 1: SSN, address).

Widen columns to accommodate Fernet ciphertext (~2-3x plaintext).
Encrypt existing clear-text data in-place.

Fields: social_security_number, address, street_number, street_name.

Revision ID: z1a2b3c4d5e6
Revises: y0z1a2b3c4d5
Create Date: 2026-04-20 18:00:00.000000
"""

import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

logger = logging.getLogger("alembic.encrypt_customer_pii")

revision: str = "z1a2b3c4d5e6"
down_revision: str = "y0z1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Widen columns to fit encrypted ciphertext
    op.alter_column("customers", "social_security_number",
                    type_=sa.String(200), existing_type=sa.String(15))
    op.alter_column("customers", "address",
                    type_=sa.String(500), existing_type=sa.String(255))
    op.alter_column("customers", "street_number",
                    type_=sa.String(200), existing_type=sa.String(20))
    op.alter_column("customers", "street_name",
                    type_=sa.String(500), existing_type=sa.String(255))

    # 2. Encrypt existing clear-text data
    from app.core.encryption import encrypt

    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, social_security_number, address, street_number, street_name FROM customers")
    ).fetchall()

    for row in rows:
        updates = {}
        if row.social_security_number:
            updates["social_security_number"] = encrypt(row.social_security_number)
        if row.address:
            updates["address"] = encrypt(row.address)
        if row.street_number:
            updates["street_number"] = encrypt(row.street_number)
        if row.street_name:
            updates["street_name"] = encrypt(row.street_name)
        if updates:
            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            conn.execute(
                sa.text(f"UPDATE customers SET {set_clause} WHERE id = :id"),
                {"id": row.id, **updates},
            )


def downgrade() -> None:
    # Decrypt data back to clear text
    from app.core.encryption import decrypt

    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, social_security_number, address, street_number, street_name FROM customers")
    ).fetchall()

    for row in rows:
        updates = {}
        for col in ("social_security_number", "address", "street_number", "street_name"):
            val = getattr(row, col)
            if val:
                try:
                    updates[col] = decrypt(val)
                except Exception as exc:
                    # Already in clear text — skip silently after warning
                    logger.warning(
                        "encrypt_customer_pii_downgrade_decrypt_skipped",
                        extra={"row_id": row.id, "column": col, "error": str(exc)},
                    )
        if updates:
            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            conn.execute(
                sa.text(f"UPDATE customers SET {set_clause} WHERE id = :id"),
                {"id": row.id, **updates},
            )

    # Shrink columns back
    op.alter_column("customers", "social_security_number",
                    type_=sa.String(15), existing_type=sa.String(200))
    op.alter_column("customers", "address",
                    type_=sa.String(255), existing_type=sa.String(500))
    op.alter_column("customers", "street_number",
                    type_=sa.String(20), existing_type=sa.String(200))
    op.alter_column("customers", "street_name",
                    type_=sa.String(255), existing_type=sa.String(500))
