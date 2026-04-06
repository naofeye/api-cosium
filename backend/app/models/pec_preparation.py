"""Models for PEC preparation (assistance PEC).

PecPreparation stores the consolidated data snapshot and user validations/corrections.
PecPreparationDocument links supporting documents to a preparation.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PecPreparation(Base):
    """A PEC preparation worksheet for a client."""

    __tablename__ = "pec_preparations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id"), nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id"), nullable=False, index=True
    )
    devis_id: Mapped[int | None] = mapped_column(
        ForeignKey("devis.id"), nullable=True, index=True
    )
    pec_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("pec_requests.id"), nullable=True, index=True
    )

    # Snapshot of consolidated data (JSON serialized ConsolidatedClientProfile)
    consolidated_data: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Preparation status
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="en_preparation", index=True
    )
    completude_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    errors_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    warnings_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # User validations/corrections (JSON)
    user_validations: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_corrections: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, onupdate=lambda: datetime.now(UTC)
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # Relationships
    documents: Mapped[list["PecPreparationDocument"]] = relationship(
        "PecPreparationDocument",
        back_populates="preparation",
        lazy="selectin",
    )


class PecPreparationDocument(Base):
    """Link between a PEC preparation and its supporting documents."""

    __tablename__ = "pec_preparation_documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    preparation_id: Mapped[int] = mapped_column(
        ForeignKey("pec_preparations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id"), nullable=True
    )
    cosium_document_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    document_role: Mapped[str] = mapped_column(
        String(50), nullable=False, default="autre"
    )
    extraction_id: Mapped[int | None] = mapped_column(
        ForeignKey("document_extractions.id"), nullable=True
    )

    # Relationships
    preparation: Mapped["PecPreparation"] = relationship(
        "PecPreparation", back_populates="documents"
    )
