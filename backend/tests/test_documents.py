import io


def test_list_documents_empty(client, auth_headers):
    create_resp = client.post(
        "/api/v1/cases",
        json={"first_name": "Doc", "last_name": "Test"},
        headers=auth_headers,
    )
    case_id = create_resp.json()["id"]
    resp = client.get(f"/api/v1/cases/{case_id}/documents", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_upload_document(client, auth_headers):
    create_resp = client.post(
        "/api/v1/cases",
        json={"first_name": "Upload", "last_name": "Test"},
        headers=auth_headers,
    )
    case_id = create_resp.json()["id"]
    file_content = io.BytesIO(b"fake pdf content")
    resp = client.post(
        f"/api/v1/cases/{case_id}/documents",
        files={"file": ("ordonnance.pdf", file_content, "application/pdf")},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["filename"] == "ordonnance.pdf"
    assert data["type"] == "uploaded"
    assert "id" in data

    # Verify it appears in list
    list_resp = client.get(f"/api/v1/cases/{case_id}/documents", headers=auth_headers)
    assert len(list_resp.json()) == 1
