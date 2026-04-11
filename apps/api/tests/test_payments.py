from app.models import Payment


def test_payment_summary_empty(client, auth_headers):
    create_resp = client.post(
        "/api/v1/cases",
        json={"first_name": "Pay", "last_name": "Test"},
        headers=auth_headers,
    )
    case_id = create_resp.json()["id"]
    resp = client.get(f"/api/v1/cases/{case_id}/payments", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == case_id
    assert data["total_due"] == 0
    assert data["total_paid"] == 0
    assert data["remaining"] == 0
    assert data["items"] == []


def test_payment_summary_with_data(client, auth_headers, db):
    create_resp = client.post(
        "/api/v1/cases",
        json={"first_name": "Pay", "last_name": "Data"},
        headers=auth_headers,
    )
    case_id = create_resp.json()["id"]
    db.add(Payment(tenant_id=1, case_id=case_id, payer_type="mutuelle", amount_due=200, amount_paid=100, status="partial"))
    db.add(Payment(tenant_id=1, case_id=case_id, payer_type="client", amount_due=50, amount_paid=50, status="paid"))
    db.commit()

    resp = client.get(f"/api/v1/cases/{case_id}/payments", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_due"] == 250
    assert data["total_paid"] == 150
    assert data["remaining"] == 100
    assert len(data["items"]) == 2
