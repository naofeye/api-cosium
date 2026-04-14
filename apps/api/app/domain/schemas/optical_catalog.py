"""Schemas Pydantic pour le catalogue optique Cosium (lecture seule)."""
from pydantic import BaseModel


class OpticalFrameResponse(BaseModel):
    """Monture du catalogue Cosium."""
    cosium_id: int | None = None
    brand: str | None = None
    model: str | None = None
    color: str | None = None
    material: str | None = None
    style: str | None = None
    size: int | None = None
    nose_width: int | None = None
    arm_size: int | None = None
    price: float | None = None


class OpticalLensResponse(BaseModel):
    """Verre du catalogue Cosium."""
    cosium_id: int | None = None
    brand: str | None = None
    model: str | None = None
    price: float | None = None
    material: str | None = None
    index: float | None = None
    treatment: str | None = None
    tint: str | None = None
    photochromic: bool | None = None
    has_options: bool = False
