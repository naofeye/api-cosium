"""Pydantic schemas for the multi-source consolidation engine."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

# Type pour les valeurs de champs heterogenes (noms, montants, dates, etc.)
FieldValue = str | int | float | bool | None


class FieldStatus(str, Enum):
    """Status of a consolidated field indicating its provenance and reliability."""

    CONFIRMED = "confirmed"  # User explicitly validated
    EXTRACTED = "extracted"  # From a reliable source (Cosium, devis)
    DEDUCED = "deduced"  # Inferred from related data or OCR
    MISSING = "missing"  # Required but absent
    CONFLICT = "conflict"  # Multiple sources disagree
    MANUAL = "manual"  # User manually entered/corrected


class ConsolidatedField(BaseModel):
    """A single consolidated field with its source, confidence, and status."""

    value: FieldValue
    source: str = Field(
        ...,
        description=(
            'Source identifier: "cosium_client" | "cosium_prescription_123" '
            '| "devis_456" | "document_ocr_789" | "manual"'
        ),
    )
    source_label: str = Field(
        ...,
        description='Human-readable label: "Cosium" | "Ordonnance du 15/03/2026"',
    )
    confidence: float = Field(..., ge=0.0, le=1.0)
    status: FieldStatus = FieldStatus.EXTRACTED
    alternatives: list[dict[str, FieldValue]] | None = None
    last_updated: datetime | None = None


class ConsolidationAlert(BaseModel):
    """An inconsistency or missing-data alert."""

    severity: str = Field(..., pattern=r"^(error|warning|info)$")
    field: str
    message: str
    sources: list[str] = []


class ConsolidatedClientProfile(BaseModel):
    """Full consolidated client profile from all data sources."""

    # Identity
    nom: ConsolidatedField | None = None
    prenom: ConsolidatedField | None = None
    date_naissance: ConsolidatedField | None = None
    numero_secu: ConsolidatedField | None = None

    # Mutuelle
    mutuelle_nom: ConsolidatedField | None = None
    mutuelle_numero_adherent: ConsolidatedField | None = None
    mutuelle_code_organisme: ConsolidatedField | None = None
    type_beneficiaire: ConsolidatedField | None = None
    date_fin_droits: ConsolidatedField | None = None

    # Optical correction (latest)
    sphere_od: ConsolidatedField | None = None
    cylinder_od: ConsolidatedField | None = None
    axis_od: ConsolidatedField | None = None
    addition_od: ConsolidatedField | None = None
    sphere_og: ConsolidatedField | None = None
    cylinder_og: ConsolidatedField | None = None
    axis_og: ConsolidatedField | None = None
    addition_og: ConsolidatedField | None = None
    ecart_pupillaire: ConsolidatedField | None = None
    prescripteur: ConsolidatedField | None = None
    date_ordonnance: ConsolidatedField | None = None

    # Equipment (from devis)
    monture: ConsolidatedField | None = None
    verres: list[ConsolidatedField] = []

    # Financial
    montant_ttc: ConsolidatedField | None = None
    part_secu: ConsolidatedField | None = None
    part_mutuelle: ConsolidatedField | None = None
    reste_a_charge: ConsolidatedField | None = None

    # Metadata
    alertes: list[ConsolidationAlert] = []
    champs_manquants: list[str] = []
    score_completude: float = Field(0.0, ge=0.0, le=100.0)
    sources_utilisees: list[str] = []

    model_config = ConfigDict(from_attributes=True)
