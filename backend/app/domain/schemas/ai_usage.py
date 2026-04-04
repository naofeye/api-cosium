"""Schemas for AI usage billing endpoints."""

from pydantic import BaseModel


class AIUsageSummary(BaseModel):
    year: int
    month: int
    total_requests: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost_usd: float = 0.0
    quota: int = 0
    quota_remaining: int = 0
    quota_percent: float = 0.0
    plan: str = "solo"


class AIUsageDaily(BaseModel):
    day: int
    requests: int = 0
    tokens: int = 0
