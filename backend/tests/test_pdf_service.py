"""Tests pour la generation PDF devis et factures."""

from fastapi.testclient import TestClient


def test_devis_pdf_generation(client: TestClient, auth_headers: dict) -> None:
    """Generer un PDF devis retourne un fichier PDF valide."""
    # Creer un case + devis
    resp = client.post(
        "/api/v1/cases",
        json={"first_name": "PDF", "last_name": "Test", "source": "test"},
        headers=auth_headers,
    )
    case_id = resp.json()["id"]

    resp = client.post(
        "/api/v1/devis",
        json={
            "case_id": case_id,
            "part_secu": 50,
            "part_mutuelle": 100,
            "lignes": [{"designation": "Monture Test", "quantite": 1, "prix_unitaire_ht": 200, "taux_tva": 20}],
        },
        headers=auth_headers,
    )
    devis_id = resp.json()["id"]

    # Telecharger le PDF
    resp = client.get(f"/api/v1/devis/{devis_id}/pdf", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:5] == b"%PDF-"
    assert len(resp.content) > 500


def test_facture_pdf_generation(client: TestClient, auth_headers: dict) -> None:
    """Generer un PDF facture retourne un fichier PDF valide."""
    # Creer case + devis + signer + generer facture
    resp = client.post(
        "/api/v1/cases",
        json={"first_name": "FactPDF", "last_name": "Test", "source": "test"},
        headers=auth_headers,
    )
    case_id = resp.json()["id"]

    resp = client.post(
        "/api/v1/devis",
        json={
            "case_id": case_id,
            "part_secu": 0,
            "part_mutuelle": 0,
            "lignes": [{"designation": "Verre", "quantite": 2, "prix_unitaire_ht": 100, "taux_tva": 20}],
        },
        headers=auth_headers,
    )
    devis_id = resp.json()["id"]
    client.patch(f"/api/v1/devis/{devis_id}/status", json={"status": "envoye"}, headers=auth_headers)
    client.patch(f"/api/v1/devis/{devis_id}/status", json={"status": "signe"}, headers=auth_headers)

    resp = client.post("/api/v1/factures", json={"devis_id": devis_id}, headers=auth_headers)
    facture_id = resp.json()["id"]

    # Telecharger le PDF
    resp = client.get(f"/api/v1/factures/{facture_id}/pdf", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.content[:5] == b"%PDF-"
    assert len(resp.content) > 500


def test_devis_pdf_not_found(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/devis/99999/pdf", headers=auth_headers)
    assert resp.status_code == 404


def test_facture_pdf_not_found(client: TestClient, auth_headers: dict) -> None:
    resp = client.get("/api/v1/factures/99999/pdf", headers=auth_headers)
    assert resp.status_code == 404
