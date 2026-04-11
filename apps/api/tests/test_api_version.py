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


def test_version_header_present_on_all_responses(client: TestClient) -> None:
    """Every API response should include X-API-Version header."""
    resp = client.get("/api/v1/version")
    assert "X-API-Version" in resp.headers
    assert re.match(r"^\d+\.\d+\.\d+$", resp.headers["X-API-Version"])


def test_version_header_on_404(client: TestClient) -> None:
    """X-API-Version header is present even on 404 responses."""
    resp = client.get("/api/v1/nonexistent-endpoint-xyz")
    assert "X-API-Version" in resp.headers


def test_powered_by_header(client: TestClient) -> None:
    """X-Powered-By header should be set to OptiFlow AI."""
    resp = client.get("/api/v1/version")
    assert resp.headers.get("X-Powered-By") == "OptiFlow AI"


def test_version_endpoint_no_auth_required(client: TestClient) -> None:
    """The version endpoint should be accessible without authentication."""
    resp = client.get("/api/v1/version")
    assert resp.status_code == 200
