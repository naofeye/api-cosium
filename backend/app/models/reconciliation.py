"""Models for dossier reconciliation — linking payments to invoices."""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DossierReconciliation(Base):
    """Reconciliation result for a single customer dossier."""

    __tablename__ = "dossier_reconciliations"
    __table_args__ = (
        Index("ix_recon_tenant_customer", "tenant_id", "customer_id", unique=True),
        Index("ix_recon_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), nullable=False, index=True)

    # Summary
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="en_attente",
    )  # solde, solde_non_rapproche, partiellement_paye, en_attente, incoherent, info_insuffisante
    confidence: Mapped[str] = mapped_column(
        String(20), nullable=False, default="incertain",
    )  # certain, probable, partiel, incertain

    # Financial totals
    total_facture: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_outstanding: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_paid: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_secu: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_mutuelle: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_client: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_avoir: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    # Counts
    invoice_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quote_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    credit_note_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # PEC info
    has_pec: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pec_status: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Detail (JSON stored as text)
    detail_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    anomalies: Mapped[str | None] = mapped_column(Text, nullable=True)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    reconciled_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC),
    )
