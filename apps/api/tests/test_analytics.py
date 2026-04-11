from fastapi.testclient import TestClient


def test_financial_kpis(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/analytics/financial", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "ca_total" in data
    assert "taux_recouvrement" in data


def test_aging_balance(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/analytics/aging", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "buckets" in data
    assert len(data["buckets"]) == 4


def test_payer_performance(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/analytics/payers", headers=auth_headers)
    assert resp.status_code == 200
    assert "payers" in resp.json()


def test_operational_kpis(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/analytics/operational", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "dossiers_en_cours" in data
    assert "taux_completude" in data


def test_commercial_kpis(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/analytics/commercial", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "taux_conversion" in data
    assert "ca_par_mois" in data
    assert len(data["ca_par_mois"]) == 6


def test_marketing_kpis(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/analytics/marketing", headers=auth_headers)
    assert resp.status_code == 200
    assert "campagnes_total" in resp.json()


def test_dashboard_full(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/analytics/dashboard", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "financial" in data
    assert "aging" in data
    assert "payers" in data
    assert "operational" in data
    assert "commercial" in data
    assert "marketing" in data
