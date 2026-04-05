"""Models for Cosium-synced data stored locally in OptiFlow.

These tables store raw Cosium data separately from OptiFlow's own business objects.
Synchronization is UNIDIRECTIONAL: Cosium -> OptiFlow only.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CosiumInvoice(Base):
    """Facture Cosium synchronisee — donnees brutes en lecture seule."""

    __tablename__ = "cosium_invoices"
    __table_args__ = (
        Index("ix_cosium_invoices_tenant_cosium", "tenant_id", "cosium_id", unique=True),
        Index("ix_cosium_invoices_tenant_date", "tenant_id", "invoice_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    cosium_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    invoice_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(30), nullable=False, default="INVOICE")
    total_ti: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    outstanding_balance: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    share_social_security: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    share_private_insurance: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    settled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    site_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CosiumProduct(Base):
    """Produit Cosium synchronise — echantillon catalogue."""

    __tablename__ = "cosium_products"
    __table_args__ = (Index("ix_cosium_products_tenant_cosium", "tenant_id", "cosium_id", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    cosium_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    code: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    ean_code: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    price: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    family_type: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
