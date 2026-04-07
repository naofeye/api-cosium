"""Models for batch PEC operations (Groupes marketing).

BatchOperation groups multiple clients for bulk PEC preparation.
BatchOperationItem tracks per-client status within a batch.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BatchOperation(Base):
    """A batch operation targeting clients linked to a marketing code (Cosium tag)."""

    __tablename__ = "batch_operations"
    __table_args__ = (
        Index("ix_batch_ops_tenant_status", "tenant_id", "status"),
        Index("ix_batch_ops_tenant_code", "tenant_id", "marketing_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="batch_entreprise"
    )
    marketing_code: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="en_cours"
    )

    # Stats
    total_clients: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clients_prets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clients_incomplets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clients_en_conflit: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clients_erreur: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    items: Mapped[list["BatchOperationItem"]] = relationship(
        "BatchOperationItem",
        back_populates="batch",
        lazy="selectin",
    )


class BatchOperationItem(Base):
    """Per-client item within a batch operation."""

    __tablename__ = "batch_operation_items"
    __table_args__ = (
        Index("ix_batch_items_batch_status", "batch_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(
        ForeignKey("batch_operations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"), nullable=False, index=True
    )

    # Status per client
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="en_attente"
    )

    # PEC preparation link
    pec_preparation_id: Mapped[int | None] = mapped_column(
        ForeignKey("pec_preparations.id"), nullable=True
    )

    # Pre-control summary
    completude_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Error details
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    processed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    batch: Mapped["BatchOperation"] = relationship(
        "BatchOperation", back_populates="items"
    )
