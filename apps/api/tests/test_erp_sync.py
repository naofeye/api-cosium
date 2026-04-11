"""Tests du service de synchronisation ERP agnostique."""

from fastapi.testclient import TestClient


def test_sync_status_endpoint(client: TestClient, auth_headers: dict) -> None:
    """GET /sync/status retourne le statut ERP."""
    resp = client.get("/api/v1/sync/status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "erp_type" in data
    assert "configured" in data
    assert data["erp_type"] == "cosium"


def test_erp_types_endpoint(client: TestClient, auth_headers: dict) -> None:
    """GET /sync/erp-types retourne la liste des ERP."""
    resp = client.get("/api/v1/sync/erp-types", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    types = {t["type"] for t in data}
    assert "cosium" in types
    # Chaque entry a type, status, label
    for t in data:
        assert "type" in t
        assert "status" in t
        assert "label" in t


def test_sync_status_requires_auth(client: TestClient) -> None:
    """Les endpoints sync necessitent une auth."""
    resp = client.get("/api/v1/sync/status")
    assert resp.status_code == 401


def test_no_direct_cosium_import_in_services() -> None:
    """Verifie qu'aucun service (hors integrations/) n'importe CosiumClient directement.

    sync_service.py est conserve pour retrocompatibilite mais ne devrait plus
    etre le point d'entree principal.
    """
    import ast
    import os

    services_dir = os.path.join(os.path.dirname(__file__), "..", "app", "services")
    violations = []

    for filename in os.listdir(services_dir):
        if not filename.endswith(".py"):
            continue
        # sync_service.py is the legacy service, allowed to import cosium
        if filename in ("sync_service.py", "__init__.py"):
            continue

        filepath = os.path.join(services_dir, filename)
        with open(filepath) as f:
            try:
                tree = ast.parse(f.read())
            except SyntaxError:
                continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if "cosium.client" in node.module and "cosium_client" in [
                    alias.name for alias in node.names
                ]:
                    violations.append(filename)

    assert violations == [], (
        f"Les services suivants importent directement CosiumClient : {violations}. "
        f"Utilisez erp_factory.get_connector() a la place."
    )
