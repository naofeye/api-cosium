"""Tests unitaires pour document_service — upload, listing, validation fichiers."""

import io

import pytest
from fastapi.testclient import TestClient


class TestListDocuments:
    """Tests du listing des documents d'un dossier."""

    def test_list_documents_empty_case(self, client: TestClient, auth_headers: dict):
        resp = client.post(
            "/api/v1/cases",
            json={"first_name": "Doc", "last_name": "Empty"},
            headers=auth_headers,
        )
        case_id = resp.json()["id"]
        resp = client.get(f"/api/v1/cases/{case_id}/documents", headers=auth_headers)

        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_documents_after_upload(self, client: TestClient, auth_headers: dict):
        resp = client.post(
            "/api/v1/cases",
            json={"first_name": "Doc", "last_name": "List"},
            headers=auth_headers,
        )
        case_id = resp.json()["id"]
        file_content = io.BytesIO(b"fake pdf content")
        client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"file": ("test.pdf", file_content, "application/pdf")},
            headers=auth_headers,
        )

        resp = client.get(f"/api/v1/cases/{case_id}/documents", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) == 1


class TestUploadDocument:
    """Tests du televersement de documents."""

    def test_upload_pdf_success(self, client: TestClient, auth_headers: dict):
        resp = client.post(
            "/api/v1/cases",
            json={"first_name": "Upload", "last_name": "PDF"},
            headers=auth_headers,
        )
        case_id = resp.json()["id"]
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
        assert "uploaded_at" in data

    def test_upload_image_jpeg(self, client: TestClient, auth_headers: dict):
        resp = client.post(
            "/api/v1/cases",
            json={"first_name": "Upload", "last_name": "JPG"},
            headers=auth_headers,
        )
        case_id = resp.json()["id"]
        file_content = io.BytesIO(b"\xff\xd8\xff\xe0fake jpeg")
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"file": ("photo.jpg", file_content, "image/jpeg")},
            headers=auth_headers,
        )

        assert resp.status_code == 201
        assert resp.json()["filename"] == "photo.jpg"

    def test_upload_rejected_extension(self, client: TestClient, auth_headers: dict):
        """Les fichiers avec une extension non autorisee doivent etre rejetes."""
        resp = client.post(
            "/api/v1/cases",
            json={"first_name": "Upload", "last_name": "Rejected"},
            headers=auth_headers,
        )
        case_id = resp.json()["id"]
        file_content = io.BytesIO(b"#!/bin/bash\nrm -rf /")
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"file": ("malicious.sh", file_content, "text/x-shellscript")},
            headers=auth_headers,
        )

        assert resp.status_code == 422

    def test_upload_rejected_mime_type(self, client: TestClient, auth_headers: dict):
        """Un fichier avec un MIME type non autorise doit etre rejete."""
        resp = client.post(
            "/api/v1/cases",
            json={"first_name": "Upload", "last_name": "BadMime"},
            headers=auth_headers,
        )
        case_id = resp.json()["id"]
        file_content = io.BytesIO(b"executable content")
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"file": ("test.pdf", file_content, "application/x-executable")},
            headers=auth_headers,
        )

        assert resp.status_code == 422

    def test_upload_oversized_file_rejected_with_streaming(
        self, client: TestClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
    ):
        """Un fichier qui depasse MAX_UPLOAD_SIZE_MB doit etre rejete sans
        charger le payload complet en memoire (audit Codex 2026-04-28 #2)."""
        from app.core.config import settings as _settings

        # Limite minuscule pour le test
        monkeypatch.setattr(_settings, "max_upload_size_mb", 1)

        resp = client.post(
            "/api/v1/cases",
            json={"first_name": "Big", "last_name": "Upload"},
            headers=auth_headers,
        )
        case_id = resp.json()["id"]

        oversized = b"%PDF" + b"\x00" * (2 * 1024 * 1024)  # 2 MB > 1 MB limit
        resp = client.post(
            f"/api/v1/cases/{case_id}/documents",
            files={"file": ("big.pdf", io.BytesIO(oversized), "application/pdf")},
            headers=auth_headers,
        )

        assert resp.status_code == 422
        assert "trop volumineux" in resp.text.lower()

    def test_upload_multiple_documents(self, client: TestClient, auth_headers: dict):
        """Verifier qu'on peut telecharger plusieurs documents sur un meme dossier."""
        resp = client.post(
            "/api/v1/cases",
            json={"first_name": "Multi", "last_name": "Upload"},
            headers=auth_headers,
        )
        case_id = resp.json()["id"]

        for name in ["doc1.pdf", "doc2.pdf", "photo.png"]:
            mime = "application/pdf" if name.endswith(".pdf") else "image/png"
            file_content = io.BytesIO(b"fake content")
            resp = client.post(
                f"/api/v1/cases/{case_id}/documents",
                files={"file": (name, file_content, mime)},
                headers=auth_headers,
            )
            assert resp.status_code == 201

        resp = client.get(f"/api/v1/cases/{case_id}/documents", headers=auth_headers)
        assert len(resp.json()) == 3


class TestDownloadDocument:
    """Tests du telechargement de documents."""

    def test_download_not_found(self, client: TestClient, auth_headers: dict):
        """Un document inexistant retourne 404."""
        resp = client.get(
            "/api/v1/documents/99999/download",
            headers=auth_headers,
            follow_redirects=False,
        )
        assert resp.status_code == 404


class TestUploadDocumentTenantIsolation:
    """Codex review 2026-05-01 #12 : un upload avec case_id inconnu/cross-tenant
    doit echouer avant de toucher S3 ou la DB."""

    def test_upload_unknown_case_returns_404(self, client: TestClient, auth_headers: dict):
        """case_id inexistant -> 404, pas de fichier orphelin S3."""
        file_content = io.BytesIO(b"%PDF-1.4 fake")
        resp = client.post(
            "/api/v1/cases/999999/documents",
            files={"file": ("orphan.pdf", file_content, "application/pdf")},
            headers=auth_headers,
        )
        assert resp.status_code == 404
