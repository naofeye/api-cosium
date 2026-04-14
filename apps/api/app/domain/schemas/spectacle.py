"""Schemas Pydantic pour les dossiers lunettes Cosium (lecture seule)."""
from pydantic import BaseModel


class DiopterEntry(BaseModel):
    """Une entree de dioptrie (mesure par type de vision) pour OD/OG."""
    sphere_right: float | None = None
    cylinder_right: float | None = None
    axis_right: float | None = None
    addition_right: float | None = None
    prism_right: float | None = None
    sphere_left: float | None = None
    cylinder_left: float | None = None
    axis_left: float | None = None
    addition_left: float | None = None
    prism_left: float | None = None
    vision_type: str | None = None


class SpectacleFileMeta(BaseModel):
    """Metadata d'un dossier lunettes Cosium."""
    cosium_id: int | None = None
    has_diopters: bool = False
    has_selection: bool = False
    has_doctor_address: bool = False
    creation_date: str | None = None


class SpectacleFileComplete(BaseModel):
    """Dossier lunettes complet : metadata + dioptries + selection."""
    file: SpectacleFileMeta
    diopters: list[DiopterEntry] = []
    selection: dict = {}
