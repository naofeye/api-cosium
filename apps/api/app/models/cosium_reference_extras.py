"""Additional Cosium reference models (split from cosium_reference.py).

These tables store reference data synced from Cosium.
Synchronization is UNIDIRECTIONAL: Cosium -> OptiFlow only.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CosiumCalendarCategory(Base):
    """Categorie d'evenement calendrier Cosium."""

    __tablename__ = "cosium_calendar_categories"
    __table_args__ = (
        Index("ix_cosium_cal_cat_tenant_name", "tenant_id", "name", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    cosium_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    family_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CosiumLensFocusType(Base):
    """Type de foyer de verre Cosium."""

    __tablename__ = "cosium_lens_focus_types"
    __table_args__ = (
        Index("ix_cosium_lft_tenant_code", "tenant_id", "code", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CosiumLensFocusCategory(Base):
    """Categorie de foyer de verre Cosium."""

    __tablename__ = "cosium_lens_focus_categories"
    __table_args__ = (
        Index("ix_cosium_lfc_tenant_code", "tenant_id", "code", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CosiumLensMaterial(Base):
    """Materiau de verre Cosium."""

    __tablename__ = "cosium_lens_materials"
    __table_args__ = (
        Index("ix_cosium_lm_tenant_code", "tenant_id", "code", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CosiumCustomerTag(Base):
    """Association tag-client Cosium (quels tags sont attribues a quel client)."""

    __tablename__ = "cosium_customer_tags"
    __table_args__ = (
        Index("ix_cosium_cust_tags_tenant_cust_tag", "tenant_id", "customer_cosium_id", "tag_code", unique=True),
        Index("ix_cosium_cust_tags_tenant_cust", "tenant_id", "customer_cosium_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    customer_cosium_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    tag_code: Mapped[str] = mapped_column(String(100), nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
