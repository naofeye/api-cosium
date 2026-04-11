def test_dashboard_summary(client, auth_headers):
    resp = client.get("/api/v1/dashboard/summary", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "cases_count" in data
    assert "documents_count" in data
    assert "alerts_count" in data
    assert "total_due" in data
    assert "total_paid" in data
    assert "remaining" in data


def test_dashboard_requires_auth(client):
    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 401
