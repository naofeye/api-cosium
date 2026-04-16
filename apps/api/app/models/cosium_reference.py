"""Models for Cosium reference data stored locally in OptiFlow.

These tables store reference/calendar data synced from Cosium.
Synchronization is UNIDIRECTIONAL: Cosium -> OptiFlow only.
"""

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CosiumCalendarEvent(Base):
    """Evenement calendrier Cosium synchronise."""

    __tablename__ = "cosium_calendar_events"
    __table_args__ = (
        Index("ix_cosium_calendar_tenant_cosium", "tenant_id", "cosium_id", unique=True),
        Index("ix_cosium_calendar_tenant_start", "tenant_id", "start_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    cosium_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    customer_fullname: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    customer_number: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    category_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    category_color: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    category_family: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    canceled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    missed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    customer_arrived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    observation: Mapped[str | None] = mapped_column(Text, nullable=True)
    site_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    modification_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CosiumMutuelle(Base):
    """Mutuelle / organisme complementaire Cosium."""

    __tablename__ = "cosium_mutuelles"
    __table_args__ = (
        Index("ix_cosium_mutuelles_tenant_cosium", "tenant_id", "cosium_id", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    cosium_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    code: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    opto_amc: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    coverage_request_phone: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    coverage_request_email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CosiumDoctor(Base):
    """Prescripteur / medecin Cosium."""

    __tablename__ = "cosium_doctors"
    __table_args__ = (
        Index("ix_cosium_doctors_tenant_cosium", "tenant_id", "cosium_id", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    cosium_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    firstname: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    lastname: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    civility: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    rpps_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    specialty: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    optic_prescriber: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    audio_prescriber: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CosiumBrand(Base):
    """Marque Cosium."""

    __tablename__ = "cosium_brands"
    __table_args__ = (
        Index("ix_cosium_brands_tenant_name", "tenant_id", "name", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CosiumSupplier(Base):
    """Fournisseur Cosium."""

    __tablename__ = "cosium_suppliers"
    __table_args__ = (
        Index("ix_cosium_suppliers_tenant_name", "tenant_id", "name", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CosiumTag(Base):
    """Tag / etiquette Cosium."""

    __tablename__ = "cosium_tags"
    __table_args__ = (
        Index("ix_cosium_tags_tenant_cosium", "tenant_id", "cosium_id", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    cosium_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CosiumSite(Base):
    """Site / magasin Cosium."""

    __tablename__ = "cosium_sites"
    __table_args__ = (
        Index("ix_cosium_sites_tenant_cosium", "tenant_id", "cosium_id", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    cosium_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    code: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    long_label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    address: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    postcode: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CosiumBank(Base):
    """Banque Cosium."""

    __tablename__ = "cosium_banks"
    __table_args__ = (
        Index("ix_cosium_banks_tenant_name", "tenant_id", "name", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    cosium_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    address: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    post_code: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CosiumCompany(Base):
    """Societe / entreprise Cosium (informations SIRET, etc.)."""

    __tablename__ = "cosium_companies"
    __table_args__ = (
        Index("ix_cosium_companies_tenant_name", "tenant_id", "name", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    cosium_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    siret: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    ape_code: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    address: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    city: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    post_code: Mapped[str] = mapped_column(String(20), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CosiumUser(Base):
    """Utilisateur / employe Cosium."""

    __tablename__ = "cosium_users"
    __table_args__ = (
        Index("ix_cosium_users_tenant_cosium", "tenant_id", "cosium_id", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    cosium_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    alias: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    firstname: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    lastname: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    bot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CosiumEquipmentType(Base):
    """Type de famille d'equipement Cosium (Lentilles, Basse Vision, Clip...)."""

    __tablename__ = "cosium_equipment_types"
    __table_args__ = (
        Index("ix_cosium_equip_types_tenant_code", "tenant_id", "label_code", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    label_code: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


class CosiumFrameMaterial(Base):
    """Materiau de monture Cosium (METAL, PLASTIQUE, TITANE...)."""

    __tablename__ = "cosium_frame_materials"
    __table_args__ = (
        Index("ix_cosium_frame_mat_tenant_code", "tenant_id", "code", unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    description: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC), nullable=False)


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
