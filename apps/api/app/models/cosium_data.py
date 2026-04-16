"""Models for Cosium-synced data stored locally in OptiFlow.

These tables store raw Cosium data separately from OptiFlow's own business objects.
Synchronization is UNIDIRECTIONAL: Cosium -> OptiFlow only.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CosiumDocument(Base):
    """Document client telecharge depuis Cosium et stocke dans MinIO."""

    __tablename__ = "cosium_documents"
    __table_args__ = (
        Index("ix_cosium_docs_tenant_cust", "tenant_id", "customer_cosium_id"),
        Index(
            "ix_cosium_docs_unique",
            "tenant_id",
            "customer_cosium_id",
            "cosium_document_id",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    customer_cosium_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    cosium_document_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_type: Mapped[str] = mapped_column(String(100), default="application/pdf", nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    minio_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CosiumInvoice(Base):
    """Facture Cosium synchronisee — donnees brutes en lecture seule."""

    __tablename__ = "cosium_invoices"
    __table_args__ = (
        Index("ix_cosium_invoices_tenant_cosium", "tenant_id", "cosium_id", unique=True),
        Index("ix_cosium_invoices_tenant_date", "tenant_id", "invoice_date"),
        Index("ix_cosium_invoices_tenant_type", "tenant_id", "type"),
        Index("ix_cosium_invoices_tenant_customer", "tenant_id", "customer_id"),
        Index("ix_cosium_invoices_tenant_outstanding", "tenant_id", "outstanding_balance"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    cosium_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    invoice_number: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    invoice_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    customer_cosium_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
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


class CosiumPayment(Base):
    """Paiement de facture Cosium."""

    __tablename__ = "cosium_payments"
    __table_args__ = (
        Index("ix_cosium_payments_tenant_cosium", "tenant_id", "cosium_id", unique=True),
        Index("ix_cosium_payments_tenant_customer", "tenant_id", "customer_id"),
        Index("ix_cosium_payments_tenant_invoice", "tenant_id", "invoice_cosium_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    cosium_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    payment_type_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    original_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    issuer_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    bank: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    site_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payment_number: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    invoice_cosium_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    customer_cosium_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CosiumThirdPartyPayment(Base):
    """Tiers payant (secu + mutuelle)."""

    __tablename__ = "cosium_third_party_payments"
    __table_args__ = (Index("ix_cosium_tpp_tenant_cosium", "tenant_id", "cosium_id", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    cosium_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    social_security_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    social_security_tpp: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    additional_health_care_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    additional_health_care_tpp: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    invoice_cosium_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CosiumPrescription(Base):
    """Ordonnance optique."""

    __tablename__ = "cosium_prescriptions"
    __table_args__ = (
        Index("ix_cosium_prescriptions_tenant_cosium", "tenant_id", "cosium_id", unique=True),
        Index("ix_cosium_prescriptions_tenant_customer", "tenant_id", "customer_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    cosium_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    prescription_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    file_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    customer_cosium_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    sphere_right: Mapped[float | None] = mapped_column(Float, nullable=True)
    cylinder_right: Mapped[float | None] = mapped_column(Float, nullable=True)
    axis_right: Mapped[float | None] = mapped_column(Float, nullable=True)
    addition_right: Mapped[float | None] = mapped_column(Float, nullable=True)
    sphere_left: Mapped[float | None] = mapped_column(Float, nullable=True)
    cylinder_left: Mapped[float | None] = mapped_column(Float, nullable=True)
    axis_left: Mapped[float | None] = mapped_column(Float, nullable=True)
    addition_left: Mapped[float | None] = mapped_column(Float, nullable=True)
    spectacles_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    prescriber_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CosiumInvoicedItem(Base):
    """Ligne de facture Cosium (produit vendu sur une facture).

    Permet la ventilation par type produit (monture/verres/lentilles/autre)
    via la famille produit. Sync depuis Cosium `/invoiced-items`.
    """

    __tablename__ = "cosium_invoiced_items"
    __table_args__ = (
        Index("ix_cosium_invoiced_items_tenant_cosium", "tenant_id", "cosium_id", unique=True),
        Index("ix_cosium_invoiced_items_tenant_invoice", "tenant_id", "invoice_cosium_id"),
        Index("ix_cosium_invoiced_items_tenant_family", "tenant_id", "product_family"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    cosium_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    invoice_cosium_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    product_cosium_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    product_label: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    product_family: Mapped[str] = mapped_column(String(100), default="", nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price_ti: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_ti: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
