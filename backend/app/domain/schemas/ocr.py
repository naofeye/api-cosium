from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExtractedDocument(BaseModel):
    """Result of text extraction from a document (PDF or image)."""

    raw_text: str = Field(..., description="Texte brut extrait du document")
    page_count: int = Field(..., ge=0, description="Nombre de pages traitees")
    extraction_method: str = Field(
        ..., description="Methode utilisee: pdfplumber, tesseract, pdfplumber+tesseract"
    )
    confidence: float | None = Field(
        None, ge=0.0, le=1.0, description="Score de confiance OCR (0-1), None si extraction native"
    )
    language: str = Field(default="fra", description="Langue detectee ou configuree")


class DocumentClassification(BaseModel):
    """Result of document type classification based on extracted text."""

    document_type: str = Field(
        ...,
        description="Type detecte: ordonnance, devis, attestation_mutuelle, facture, carte_mutuelle, autre",
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Score de confiance de la classification")
    keywords_found: list[str] = Field(default_factory=list, description="Mots-cles detectes dans le texte")


class DocumentExtractionResponse(BaseModel):
    """Response for a document extraction record."""

    id: int
    document_id: int | None
    cosium_document_id: int | None
    raw_text: str
    document_type: str | None
    classification_confidence: float | None
    extraction_method: str
    ocr_confidence: float | None
    structured_data: str | None
    extracted_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExtractionRequest(BaseModel):
    """Request payload for triggering document extraction."""

    force: bool = Field(default=False, description="Re-extraire meme si deja fait")
