"""Tests de suivi de consommation IA."""
import pytest
from datetime import datetime, timezone
from app.models import AiUsageLog


def test_ai_usage_empty(client, auth_headers):
    resp = client.get("/api/v1/ai/usage", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_requests"] == 0
    assert data["quota"] > 0
    assert data["quota_remaining"] > 0


def test_ai_usage_with_logs(client, auth_headers, db, default_tenant):
    # Insert some usage logs
    for i in range(3):
        db.add(AiUsageLog(
            tenant_id=default_tenant.id,
            user_id=1,
            copilot_type="dossier",
            model_used="claude-haiku",
            tokens_in=100 + i * 10,
            tokens_out=200 + i * 20,
            cost_usd=0.001,
        ))
    db.commit()

    resp = client.get("/api/v1/ai/usage", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_requests"] == 3
    assert data["total_tokens_in"] == 330  # 100+110+120
    assert data["total_tokens_out"] == 660  # 200+220+240
    assert data["quota_remaining"] == data["quota"] - 3


def test_ai_usage_daily(client, auth_headers, db, default_tenant):
    db.add(AiUsageLog(
        tenant_id=default_tenant.id,
        user_id=1,
        copilot_type="financier",
        model_used="claude-haiku",
        tokens_in=50,
        tokens_out=100,
        cost_usd=0.0005,
    ))
    db.commit()

    now = datetime.now(timezone.utc)
    resp = client.get(
        f"/api/v1/ai/usage/daily?year={now.year}&month={now.month}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["requests"] >= 1
