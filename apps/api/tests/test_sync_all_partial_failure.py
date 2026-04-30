"""Regression : sync_all_tenants ne doit PAS marquer un tenant comme done
si un seul domaine a echoue (sinon le compteur synced + idempotence Redis
masquent l erreur pendant 1h)."""

from unittest.mock import MagicMock, patch


def test_sync_all_does_not_mark_tenant_done_on_partial_domain_failure() -> None:
    from app.tasks.sync_tasks import _sync_all

    fake_tenant = MagicMock(id=42, name="Tenant42")

    with (
        patch("app.db.session.SessionLocal", return_value=MagicMock()),
        patch.object(_sync_all, "_sync_single_tenant") as mock_sync,
        patch("app.repositories.onboarding_repo.get_active_cosium_tenants", return_value=[fake_tenant]),
        patch("app.core.redis_cache.acquire_lock", return_value=True),
        patch("app.core.redis_cache.release_lock"),
        patch("app.core.redis_cache.get_redis_client", return_value=None),
        patch("app.core.sentry_helpers.report_incident_to_sentry"),
    ):
        # Un domaine echoue : le contrat de _sync_single_tenant met "error" dans le dict
        mock_sync.return_value = {
            "customers": {"created": 1, "updated": 0, "total": 1},
            "invoices": {"error": "Cosium 502"},
        }

        try:
            _sync_all.sync_all_tenants.run()
            # Avec un domaine en echec, sync_all_tenants raise RuntimeError (failed > 0)
            raise AssertionError("Expected RuntimeError for partial failure")
        except RuntimeError as e:
            assert "1/1 tenants failed" in str(e)


def test_sync_all_marks_tenant_done_when_all_domains_succeed() -> None:
    from app.tasks.sync_tasks import _sync_all

    fake_tenant = MagicMock(id=43, name="Tenant43")
    redis_mock = MagicMock()
    redis_mock.exists.return_value = False

    with (
        patch("app.db.session.SessionLocal", return_value=MagicMock()),
        patch.object(_sync_all, "_sync_single_tenant") as mock_sync,
        patch("app.repositories.onboarding_repo.get_active_cosium_tenants", return_value=[fake_tenant]),
        patch("app.core.redis_cache.acquire_lock", return_value=True),
        patch("app.core.redis_cache.release_lock"),
        patch("app.core.redis_cache.get_redis_client", return_value=redis_mock),
    ):
        mock_sync.return_value = {
            "customers": {"created": 1, "total": 1},
            "invoices": {"created": 0, "total": 0},
        }

        result = _sync_all.sync_all_tenants.run()
        assert result == {"synced": 1, "failed": 0, "total": 1}
        # idempotence Redis posee uniquement quand tout va bien
        redis_mock.setex.assert_called_once()
