"""Model for PEC audit trail entries.

Provides a structured, queryable audit trail for every action
performed on a PEC preparation (field validations, corrections,
refreshes, submissions, document attachments).
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PecAuditEntry(Base):
    """A single audit entry for a PEC preparation action."""

    __tablename__ = "pec_audit_entries"
    __table_args__ = (
        Index("ix_pec_audit_tenant", "tenant_id"),
        Index("ix_pec_audit_preparation", "preparation_id"),
        Index("ix_pec_audit_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), nullable=False,
    )
    preparation_id: Mapped[int] = mapped_column(
        ForeignKey("pec_preparations.id", ondelete="CASCADE"), nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(50), nullable=False,
    )  # "created", "field_validated", "field_corrected", "refreshed", "submitted", "document_attached"
    field_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
    )
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False,
    )
