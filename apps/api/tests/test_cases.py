def test_create_case(client, auth_headers):
    resp = client.post(
        "/api/v1/cases",
        json={
            "first_name": "Jean",
            "last_name": "Martin",
            "phone": "0612345678",
            "email": "jean@example.com",
            "source": "manual",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["customer_name"] == "Jean Martin"
    assert data["status"] == "draft"
    assert data["source"] == "manual"
    assert "id" in data


def test_list_cases(client, auth_headers):
    # Create one first
    client.post(
        "/api/v1/cases",
        json={"first_name": "A", "last_name": "B"},
        headers=auth_headers,
    )
    resp = client.get("/api/v1/cases", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_case_detail(client, auth_headers):
    create_resp = client.post(
        "/api/v1/cases",
        json={"first_name": "Marie", "last_name": "Dupont"},
        headers=auth_headers,
    )
    case_id = create_resp.json()["id"]
    resp = client.get(f"/api/v1/cases/{case_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == case_id
    assert data["customer_name"] == "Marie Dupont"
    assert "documents" in data
    assert "payments" in data


def test_case_not_found(client, auth_headers):
    resp = client.get("/api/v1/cases/99999", headers=auth_headers)
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "NOT_FOUND"
