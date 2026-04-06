"""Add document_extractions table

Revision ID: l7f8g9h0i1j2
Revises: k6e7f8g9h0i1
Create Date: 2026-04-05 23:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "l7f8g9h0i1j2"
down_revision: Union[str, None] = "k6e7f8g9h0i1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "document_extractions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("document_id", sa.Integer(), sa.ForeignKey("documents.id"), nullable=True, index=True),
        sa.Column("cosium_document_id", sa.Integer(), nullable=True, index=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("document_type", sa.String(50), nullable=True),
        sa.Column("classification_confidence", sa.Float(), nullable=True),
        sa.Column("extraction_method", sa.String(50), nullable=True),
        sa.Column("ocr_confidence", sa.Float(), nullable=True),
        sa.Column("structured_data", sa.Text(), nullable=True),
        sa.Column("extracted_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("document_extractions")
