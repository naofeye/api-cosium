"""Regression : POST /api/v1/sync/seed-demo doit etre refuse en staging/production.
seed-demo importe tests.factories.seed et n a aucune raison d etre exposable hors dev."""

import pytest
from fastapi import HTTPException
from unittest.mock import MagicMock, patch


def _call_seed_demo(app_env: str):
    """Appel direct du handler en bypassant rate-limiter et auth (test unitaire)."""
    from app.api.routers.sync._meta import seed_demo

    with patch("app.api.routers.sync._meta.settings") as mock_settings:
        mock_settings.app_env = app_env
        return seed_demo(db=MagicMock(), tenant_ctx=MagicMock())


def test_seed_demo_forbidden_in_production() -> None:
    with pytest.raises(HTTPException) as exc:
        _call_seed_demo("production")
    assert exc.value.status_code == 403
    assert "non-dev" in exc.value.detail.lower()


def test_seed_demo_forbidden_in_staging() -> None:
    with pytest.raises(HTTPException) as exc:
        _call_seed_demo("staging")
    assert exc.value.status_code == 403


def test_seed_demo_allowed_in_local() -> None:
    # En env dev/local/test, seed-demo passe le garde-fou et appelle seed_demo_data
    from app.api.routers.sync._meta import seed_demo

    with (
        patch("app.api.routers.sync._meta.settings") as mock_settings,
        patch("tests.factories.seed.seed_demo_data") as mock_seed,
    ):
        mock_settings.app_env = "local"
        mock_seed.return_value = MagicMock()
        seed_demo(db=MagicMock(), tenant_ctx=MagicMock())
        mock_seed.assert_called_once()
