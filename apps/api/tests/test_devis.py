from fastapi.testclient import TestClient


def _create_case(client: TestClient, headers: dict) -> int:
    resp = client.post(
        "/api/v1/cases",
        json={"first_name": "Devis", "last_name": "Test", "source": "manual"},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["id"]


LIGNES = [
    {"designation": "Monture Ray-Ban", "quantite": 1, "prix_unitaire_ht": 120.0, "taux_tva": 20.0},
    {"designation": "Verres progressifs", "quantite": 2, "prix_unitaire_ht": 85.0, "taux_tva": 20.0},
    {"designation": "Traitement anti-reflet", "quantite": 2, "prix_unitaire_ht": 30.0, "taux_tva": 20.0},
]


def test_create_devis(client: TestClient, auth_headers: dict) -> None:
    case_id = _create_case(client, auth_headers)
    resp = client.post(
        "/api/v1/devis",
        json={"case_id": case_id, "part_secu": 50.0, "part_mutuelle": 100.0, "lignes": LIGNES},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["numero"].startswith("DEV-")
    assert data["status"] == "brouillon"
    # HT: 120 + 170 + 60 = 350
    assert data["montant_ht"] == 350.0
    # TTC: 144 + 204 + 72 = 420
    assert data["montant_ttc"] == 420.0
    # TVA: 420 - 350 = 70
    assert data["tva"] == 70.0
    # Reste: 420 - 50 - 100 = 270
    assert data["reste_a_charge"] == 270.0


def test_list_devis(client: TestClient, auth_headers: dict) -> None:
    case_id = _create_case(client, auth_headers)
    client.post(
        "/api/v1/devis",
        json={"case_id": case_id, "part_secu": 0, "part_mutuelle": 0, "lignes": LIGNES[:1]},
        headers=auth_headers,
    )
    resp = client.get("/api/v1/devis", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_get_devis_detail(client: TestClient, auth_headers: dict) -> None:
    case_id = _create_case(client, auth_headers)
    resp = client.post(
        "/api/v1/devis",
        json={"case_id": case_id, "part_secu": 0, "part_mutuelle": 0, "lignes": LIGNES},
        headers=auth_headers,
    )
    devis_id = resp.json()["id"]
    resp = client.get(f"/api/v1/devis/{devis_id}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["lignes"]) == 3
    assert data["customer_name"] is not None


def test_update_devis(client: TestClient, auth_headers: dict) -> None:
    case_id = _create_case(client, auth_headers)
    resp = client.post(
        "/api/v1/devis",
        json={"case_id": case_id, "part_secu": 0, "part_mutuelle": 0, "lignes": LIGNES[:1]},
        headers=auth_headers,
    )
    devis_id = resp.json()["id"]
    resp = client.put(
        f"/api/v1/devis/{devis_id}",
        json={"part_secu": 20.0, "part_mutuelle": 30.0},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["part_secu"] == 20.0
    assert resp.json()["reste_a_charge"] == 94.0  # 144 - 20 - 30


def test_status_workflow(client: TestClient, auth_headers: dict) -> None:
    case_id = _create_case(client, auth_headers)
    resp = client.post(
        "/api/v1/devis",
        json={"case_id": case_id, "part_secu": 0, "part_mutuelle": 0, "lignes": LIGNES[:1]},
        headers=auth_headers,
    )
    devis_id = resp.json()["id"]

    # brouillon -> envoye
    resp = client.patch(
        f"/api/v1/devis/{devis_id}/status",
        json={"status": "envoye"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "envoye"

    # envoye -> signe
    resp = client.patch(
        f"/api/v1/devis/{devis_id}/status",
        json={"status": "signe"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "signe"

    # signe -> facture
    resp = client.patch(
        f"/api/v1/devis/{devis_id}/status",
        json={"status": "facture"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "facture"


def test_invalid_transition(client: TestClient, auth_headers: dict) -> None:
    case_id = _create_case(client, auth_headers)
    resp = client.post(
        "/api/v1/devis",
        json={"case_id": case_id, "part_secu": 0, "part_mutuelle": 0, "lignes": LIGNES[:1]},
        headers=auth_headers,
    )
    devis_id = resp.json()["id"]

    # brouillon -> signe (interdit, doit passer par envoye)
    resp = client.patch(
        f"/api/v1/devis/{devis_id}/status",
        json={"status": "signe"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_cannot_edit_sent_devis(client: TestClient, auth_headers: dict) -> None:
    case_id = _create_case(client, auth_headers)
    resp = client.post(
        "/api/v1/devis",
        json={"case_id": case_id, "part_secu": 0, "part_mutuelle": 0, "lignes": LIGNES[:1]},
        headers=auth_headers,
    )
    devis_id = resp.json()["id"]
    client.patch(f"/api/v1/devis/{devis_id}/status", json={"status": "envoye"}, headers=auth_headers)

    resp = client.put(
        f"/api/v1/devis/{devis_id}",
        json={"part_secu": 100},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def _create_devis_with_email(client: TestClient, headers: dict, email: str | None) -> int:
    payload = {"first_name": "Email", "last_name": "Recipient", "source": "manual"}
    if email is not None:
        payload["email"] = email
    case_resp = client.post("/api/v1/cases", json=payload, headers=headers)
    case_id = case_resp.json()["id"]
    devis_resp = client.post(
        "/api/v1/devis",
        json={"case_id": case_id, "part_secu": 0, "part_mutuelle": 0, "lignes": LIGNES[:1]},
        headers=headers,
    )
    return devis_resp.json()["id"]


def test_send_devis_email_uses_provided_recipient(
    client: TestClient, auth_headers: dict, monkeypatch
) -> None:
    """POST /devis/{id}/send-email envoie via EmailSender avec le PDF attache."""
    devis_id = _create_devis_with_email(client, auth_headers, email="client@example.com")

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
        f"/api/v1/devis/{devis_id}/send-email",
        json={"to": "override@example.com", "subject": "Devis personnalise", "message": "Bonjour, voici le devis."},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["sent"] is True
    assert body["to"] == "override@example.com"
    assert body["devis_id"] == devis_id

    assert captured["to"] == "override@example.com"
    assert captured["subject"] == "Devis personnalise"
    assert "Bonjour, voici le devis." in captured["body_html"]
    assert len(captured["attachments"]) == 1
    att = captured["attachments"][0]
    assert att.filename.startswith("devis_DEV-")
    assert att.filename.endswith(".pdf")
    assert att.mime_type == "application/pdf"
    assert isinstance(att.content, bytes | bytearray)
    assert len(att.content) > 0


def test_send_devis_email_falls_back_to_client_email(
    client: TestClient, auth_headers: dict, monkeypatch
) -> None:
    """Sans 'to' explicite, l'email du client est utilise par defaut."""
    devis_id = _create_devis_with_email(client, auth_headers, email="default@example.com")

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
        f"/api/v1/devis/{devis_id}/send-email",
        json={"to": "default@example.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert captured["to"] == "default@example.com"
    assert "DEV-" in captured["subject"]


def test_send_devis_email_returns_400_when_smtp_fails(
    client: TestClient, auth_headers: dict, monkeypatch
) -> None:
    """Si EmailSender retourne False, le service leve une BusinessError -> 400."""
    devis_id = _create_devis_with_email(client, auth_headers, email="client@example.com")

    from app.integrations import email_sender as email_sender_module

    monkeypatch.setattr(
        email_sender_module.EmailSender,
        "send_email",
        lambda self, **kwargs: False,
        raising=False,
    )

    resp = client.post(
        f"/api/v1/devis/{devis_id}/send-email",
        json={"to": "client@example.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_send_devis_email_404_for_unknown_devis(
    client: TestClient, auth_headers: dict
) -> None:
    resp = client.post(
        "/api/v1/devis/999999/send-email",
        json={"to": "client@example.com"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_send_devis_email_validates_email_format(
    client: TestClient, auth_headers: dict
) -> None:
    devis_id = _create_devis_with_email(client, auth_headers, email="client@example.com")
    resp = client.post(
        f"/api/v1/devis/{devis_id}/send-email",
        json={"to": "not-an-email"},
        headers=auth_headers,
    )
    assert resp.status_code == 422
