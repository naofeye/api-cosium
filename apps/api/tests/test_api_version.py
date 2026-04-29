"""Tests for the /api/v1/version endpoint and X-API-Version header."""

import re

from fastapi.testclient import TestClient


def test_version_endpoint_returns_correct_format(client: TestClient) -> None:
    """GET /api/v1/version returns version, api prefix, and build date."""
    resp = client.get("/api/v1/version")
    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data
    assert "api" in data
    assert "build" in data
    # Version must be semver-like (X.Y.Z)
    assert re.match(r"^\d+\.\d+\.\d+$", data["version"]), f"Version {data['version']} is not semver"
    assert data["api"] == "v1"
    # Build date should be a valid date string
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", data["build"]), f"Build {data['build']} is not a date"


def test_no_version_fingerprint_header(client: TestClient) -> None:
    """X-API-Version etait expose en clair, vecteur de reconnaissance pour
    correler la stack a des CVE. Retire post-audit (cf middleware_setup.py).
    La version reste dispo via /api/v1/version (endpoint dedie)."""
    resp = client.get("/api/v1/version")
    assert "X-API-Version" not in resp.headers
    # La version reste accessible via le body de l'endpoint dedie
    assert re.match(r"^\d+\.\d+\.\d+$", resp.json()["version"])


def test_no_version_header_on_404(client: TestClient) -> None:
    """Pas de fingerprint sur les 404 non plus."""
    resp = client.get("/api/v1/nonexistent-endpoint-xyz")
    assert "X-API-Version" not in resp.headers


def test_no_powered_by_header(client: TestClient) -> None:
    """X-Powered-By retire post-audit (fingerprint)."""
    resp = client.get("/api/v1/version")
    assert "X-Powered-By" not in resp.headers


def test_version_endpoint_no_auth_required(client: TestClient) -> None:
    """The version endpoint should be accessible without authentication."""
    resp = client.get("/api/v1/version")
    assert resp.status_code == 200
