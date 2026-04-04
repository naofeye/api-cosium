import io
from fastapi.testclient import TestClient


def _create_case(client: TestClient, headers: dict) -> int:
    resp = client.post(
        "/api/v1/cases",
        json={"first_name": "Bank", "last_name": "Test", "source": "manual"},
        headers=headers,
    )
    return resp.json()["id"]


def test_create_payment(client: TestClient, auth_headers: dict) -> None:
    case_id = _create_case(client, auth_headers)
    resp = client.post(
        "/api/v1/paiements",
        json={"case_id": case_id, "payer_type": "client", "amount_due": 100, "amount_paid": 100,
              "mode_paiement": "cb", "reference_externe": "REF-001"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "paid"
    assert data["mode_paiement"] == "cb"


def test_idempotency(client: TestClient, auth_headers: dict) -> None:
    case_id = _create_case(client, auth_headers)
    headers = {**auth_headers, "X-Idempotency-Key": "unique-key-123"}
    resp1 = client.post(
        "/api/v1/paiements",
        json={"case_id": case_id, "payer_type": "client", "amount_due": 50, "amount_paid": 50},
        headers=headers,
    )
    resp2 = client.post(
        "/api/v1/paiements",
        json={"case_id": case_id, "payer_type": "client", "amount_due": 50, "amount_paid": 50},
        headers=headers,
    )
    assert resp1.json()["id"] == resp2.json()["id"]


def test_import_csv(client: TestClient, auth_headers: dict) -> None:
    csv_content = "date;libelle;montant;reference\n01/04/2026;Paiement client;100,50;REF-001\n02/04/2026;Virement mutuelle;250,00;VIR-002\n"
    files = {"file": ("releve.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    resp = client.post("/api/v1/banking/import-statement", files=files, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["imported"] == 2


def test_list_transactions(client: TestClient, auth_headers: dict) -> None:
    csv_content = "date;libelle;montant;reference\n01/04/2026;Test;10,00;REF-X\n"
    files = {"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    client.post("/api/v1/banking/import-statement", files=files, headers=auth_headers)
    resp = client.get("/api/v1/banking/transactions", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


def test_unmatched(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/banking/unmatched", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_auto_reconcile(client: TestClient, auth_headers: dict) -> None:
    resp = client.post("/api/v1/banking/reconcile", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "matched" in data
    assert "unmatched" in data


def test_manual_match(client: TestClient, auth_headers: dict) -> None:
    case_id = _create_case(client, auth_headers)
    # Create payment
    resp = client.post(
        "/api/v1/paiements",
        json={"case_id": case_id, "payer_type": "client", "amount_due": 75, "amount_paid": 75,
              "reference_externe": "MATCH-REF"},
        headers=auth_headers,
    )
    payment_id = resp.json()["id"]

    # Import transaction
    csv_content = "date;libelle;montant;reference\n01/04/2026;Match test;75,00;MATCH-REF\n"
    files = {"file": ("match.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    client.post("/api/v1/banking/import-statement", files=files, headers=auth_headers)

    # Get unmatched to find our tx
    resp = client.get("/api/v1/banking/unmatched", headers=auth_headers)
    unmatched = resp.json()
    tx_id = next((t["id"] for t in unmatched if t["reference"] == "MATCH-REF"), None)
    if tx_id:
        resp = client.post(
            "/api/v1/banking/match",
            json={"transaction_id": tx_id, "payment_id": payment_id},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["reconciled"] is True
