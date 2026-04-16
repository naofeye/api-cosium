"""Endpoint de collecte des Core Web Vitals depuis le frontend.

Appele par `apps/web/src/components/layout/WebVitals.tsx` via `navigator.sendBeacon`.
Pas d'authentification : les payload sont anonymes (id metric + path + valeur).
Logs structure uniquement — a brancher sur Prometheus/Grafana plus tard si besoin.
"""
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.core.logging import get_logger

router = APIRouter(prefix="/api/v1", tags=["observability"])
logger = get_logger("web_vitals")


class WebVitalPayload(BaseModel):
    name: str = Field(..., max_length=20)
    value: float
    id: str = Field(..., max_length=100)
    rating: str | None = Field(default=None, max_length=20)
    path: str = Field(default="", max_length=500)


@router.post(
    "/web-vitals",
    include_in_schema=False,
    summary="Collecte Core Web Vitals frontend",
)
async def report_web_vitals(payload: WebVitalPayload, request: Request) -> dict:
    logger.info(
        "web_vital",
        name=payload.name,
        value=round(payload.value, 2),
        rating=payload.rating,
        path=payload.path,
        user_agent=request.headers.get("user-agent", "")[:200],
    )
    return {"ok": True}
