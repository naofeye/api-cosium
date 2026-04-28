from fastapi.testclient import TestClient


def _create_signed_devis(client: TestClient, headers: dict) -> int:
    """Create a case, create a devis, sign it, return devis_id."""
    resp = client.post(
        "/api/v1/cases",
        json={"first_name": "Facture", "last_name": "Test", "source": "manual"},
        headers=headers,
    )
    case_id = resp.json()["id"]

    resp = client.post(
        "/api/v1/devis",
        json={
            "case_id": case_id,
            "part_secu": 50,
            "part_mutuelle": 80,
            "lignes": [
                {"designation": "Monture", "quantite": 1, "prix_unitaire_ht": 200, "taux_tva": 20},
                {"designation": "Verres", "quantite": 2, "prix_unitaire_ht": 100, "taux_tva": 20},
            ],
        },
        headers=headers,
    )
    devis_id = resp.json()["id"]

    # brouillon -> envoye -> signe
    client.patch(f"/api/v1/devis/{devis_id}/status", json={"status": "envoye"}, headers=headers)
    client.patch(f"/api/v1/devis/{devis_id}/status", json={"status": "signe"}, headers=headers)
    return devis_id


def test_create_facture(client: TestClient, auth_headers: dict) -> None:
    devis_id = _create_signed_devis(client, auth_headers)
    resp = client.post(
        "/api/v1/factures",
        json={"devis_id": devis_id},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["numero"].startswith("F-")
    assert data["montant_ttc"] == 480.0  # (200 + 200) * 1.2 = 480
    assert data["montant_ht"] == 400.0
    assert data["tva"] == 80.0
    assert data["status"] == "emise"


def test_cannot_create_facture_from_draft(client: TestClient, auth_headers: dict) -> None:
    resp = client.post(
        "/api/v1/cases",
        json={"first_name": "Draft", "last_name": "Test", "source": "manual"},
        headers=auth_headers,
    )
    case_id = resp.json()["id"]
    resp = client.post(
        "/api/v1/devis",
        json={"case_id": case_id, "part_secu": 0, "part_mutuelle": 0,
              "lignes": [{"designation": "X", "quantite": 1, "prix_unitaire_ht": 10, "taux_tva": 20}]},
        headers=auth_headers,
    )
    devis_id = resp.json()["id"]
    resp = client.post(
        "/api/v1/factures",
        json={"devis_id": devis_id},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_duplicate_facture_is_idempotent(client: TestClient, auth_headers: dict) -> None:
    devis_id = _create_signed_devis(client, auth_headers)
    resp1 = client.post("/api/v1/factures", json={"devis_id": devis_id}, headers=auth_headers)
    assert resp1.status_code == 201
    resp2 = client.post("/api/v1/factures", json={"devis_id": devis_id}, headers=auth_headers)
    assert resp2.status_code == 201
    assert resp1.json()["id"] == resp2.json()["id"]
    assert resp1.json()["numero"] == resp2.json()["numero"]


def test_list_factures(client: TestClient, auth_headers: dict) -> None:
    devis_id = _create_signed_devis(client, auth_headers)
    client.post("/api/v1/factures", json={"devis_id": devis_id}, headers=auth_headers)
    resp = client.get("/api/v1/factures", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_get_facture_detail(client: TestClient, auth_headers: dict) -> None:
    devis_id = _create_signed_devis(client, auth_headers)
    resp = client.post("/api/v1/factures", json={"devis_id": devis_id}, headers=auth_headers)
    facture_id = resp.json()["id"]
    resp = client.get(f"/api/v1/factures/{facture_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["lignes"]) == 2
    assert data["customer_name"] is not None
    assert data["devis_numero"] is not None


def test_devis_status_changes_to_facture(client: TestClient, auth_headers: dict) -> None:
    devis_id = _create_signed_devis(client, auth_headers)
    client.post("/api/v1/factures", json={"devis_id": devis_id}, headers=auth_headers)
    resp = client.get(f"/api/v1/devis/{devis_id}", headers=auth_headers)
    assert resp.json()["status"] == "facture"


def _create_facture_with_email(
    client: TestClient, headers: dict, email: str | None
) -> int:
    """Create a case (with email), devis, sign, generate facture, return facture_id."""
    payload = {"first_name": "Email", "last_name": "Recipient", "source": "manual"}
    if email is not None:
        payload["email"] = email
    case_resp = client.post("/api/v1/cases", json=payload, headers=headers)
    case_id = case_resp.json()["id"]
    devis_resp = client.post(
        "/api/v1/devis",
        json={
            "case_id": case_id,
            "part_secu": 0,
            "part_mutuelle": 0,
            "lignes": [
                {"designation": "X", "quantite": 1, "prix_unitaire_ht": 100, "taux_tva": 20}
            ],
        },
        headers=headers,
    )
    devis_id = devis_resp.json()["id"]
    client.patch(f"/api/v1/devis/{devis_id}/status", json={"status": "envoye"}, headers=headers)
    client.patch(f"/api/v1/devis/{devis_id}/status", json={"status": "signe"}, headers=headers)
    facture_resp = client.post(
        "/api/v1/factures", json={"devis_id": devis_id}, headers=headers
    )
    return facture_resp.json()["id"]


def test_send_facture_email_uses_provided_recipient(
    client: TestClient, auth_headers: dict, monkeypatch
) -> None:
    facture_id = _create_facture_with_email(client, auth_headers, email="client@example.com")

    captured: dict = {}

    def fake_send(self, to, subject, body_html, attachments=None):
        captured["to"] = to
        captured["subject"] = subject
        captured["body_html"] = body_html
        captured["attachments"] = attachments or []
        return True

    from app.integrations import email_sender as email_sender_module

    monkeypatch.setattr(
        email_sender_module.EmailSender, "send_email", fake_send, raising=False
    )

    resp = client.post(
        f"/api/v1/factures/{facture_id}/send-email",
        json={"to": "override@example.com", "subject": "Facture custom", "message": "Bonjour, voici votre facture."},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["sent"] is True
    assert body["to"] == "override@example.com"
    assert body["facture_id"] == facture_id

    assert captured["to"] == "override@example.com"
    assert "Bonjour, voici votre facture." in captured["body_html"]
    assert len(captured["attachments"]) == 1
    att = captured["attachments"][0]
    assert att.filename.startswith("facture_F-")
    assert att.filename.endswith(".pdf")
    assert att.mime_type == "application/pdf"
    assert isinstance(att.content, bytes | bytearray)
    assert len(att.content) > 0


def test_send_facture_email_falls_back_to_client_email(
    client: TestClient, auth_headers: dict, monkeypatch
) -> None:
    facture_id = _create_facture_with_email(client, auth_headers, email="default@example.com")

    captured: dict = {}

    def fake_send(self, to, subject, body_html, attachments=None):
        captured["to"] = to
        captured["subject"] = subject
        return True

    from app.integrations import email_sender as email_sender_module

    monkeypatch.setattr(
        email_sender_module.EmailSender, "send_email", fake_send, raising=False
    )

    resp = client.post(
        f"/api/v1/factures/{facture_id}/send-email",
        json={"to": "default@example.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert captured["to"] == "default@example.com"
    assert "F-" in captured["subject"]


def test_send_facture_email_returns_400_when_smtp_fails(
    client: TestClient, auth_headers: dict, monkeypatch
) -> None:
    facture_id = _create_facture_with_email(client, auth_headers, email="client@example.com")

    from app.integrations import email_sender as email_sender_module

    monkeypatch.setattr(
        email_sender_module.EmailSender,
        "send_email",
        lambda self, **kwargs: False,
        raising=False,
    )

    resp = client.post(
        f"/api/v1/factures/{facture_id}/send-email",
        json={"to": "client@example.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_send_facture_email_404_for_unknown_facture(
    client: TestClient, auth_headers: dict
) -> None:
    resp = client.post(
        "/api/v1/factures/999999/send-email",
        json={"to": "client@example.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_send_facture_email_validates_email_format(
    client: TestClient, auth_headers: dict
) -> None:
    facture_id = _create_facture_with_email(client, auth_headers, email="client@example.com")
    resp = client.post(
        f"/api/v1/factures/{facture_id}/send-email",
        json={"to": "not-an-email"},
        headers=auth_headers,
    )
    assert resp.status_code == 422
