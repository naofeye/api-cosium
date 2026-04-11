from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_tenant_id", "tenant_id"),
        Index("ix_payments_tenant_status", "tenant_id", "status"),
        Index("ix_payments_tenant_idempotency", "tenant_id", "idempotency_key", unique=True),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), nullable=False, index=True)
    facture_id: Mapped[int | None] = mapped_column(ForeignKey("factures.id"), nullable=True, index=True)
    payer_type: Mapped[str] = mapped_column(String(50), nullable=False)
    mode_paiement: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_externe: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date_paiement: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    amount_due: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)

    case: Mapped["Case"] = relationship("Case", back_populates="payments", lazy="noload")  # type: ignore[name-defined]  # noqa: F821


class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    libelle: Mapped[str] = mapped_column(String(500), nullable=False)
    montant: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_file: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reconciled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reconciled_payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
