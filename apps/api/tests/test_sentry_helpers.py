"""Tests helper Sentry (alerting incidents)."""

from unittest.mock import MagicMock, patch


class TestReportIncidentToSentry:
    def test_noop_when_sentry_dsn_empty(self, monkeypatch):
        """Sans Sentry configure -> pas d'import, pas d'exception levee."""
        from app.core import sentry_helpers

        # settings.sentry_dsn est vide en test -> no-op
        monkeypatch.setattr("app.core.config.settings.sentry_dsn", "")
        sentry_helpers.report_incident_to_sentry(
            RuntimeError("test"),
            "test_tag",
            category="test",
        )
        # Si on arrive ici sans exception, OK.

    def test_calls_sentry_when_dsn_configured(self, monkeypatch):
        """Si Sentry DSN present, capture_exception est appele avec les tags."""
        from app.core import sentry_helpers

        monkeypatch.setattr("app.core.config.settings.sentry_dsn", "https://fake@sentry.io/1")

        mock_sentry = MagicMock()
        mock_scope = MagicMock()
        mock_sentry.push_scope.return_value.__enter__.return_value = mock_scope
        mock_sentry.push_scope.return_value.__exit__.return_value = False

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            exc = RuntimeError("test error")
            sentry_helpers.report_incident_to_sentry(
                exc,
                "my_tag",
                category="sync",
                tenant_id=42,
                domain="customers",
            )

        mock_sentry.capture_exception.assert_called_once_with(exc)
        # Tags set dans le scope
        tag_calls = {call.args[0]: call.args[1] for call in mock_scope.set_tag.call_args_list}
        assert tag_calls["incident_category"] == "sync"
        assert tag_calls["incident"] == "my_tag"
        assert tag_calls["tenant_id"] == "42"
        assert tag_calls["domain"] == "customers"

    def test_sentry_exception_does_not_propagate(self, monkeypatch):
        """Si Sentry lui-meme plante, le helper ne remonte PAS l'exception."""
        from app.core import sentry_helpers

        monkeypatch.setattr("app.core.config.settings.sentry_dsn", "https://fake@sentry.io/1")

        mock_sentry = MagicMock()
        mock_sentry.push_scope.side_effect = RuntimeError("Sentry broken")

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            # Ne doit pas lever
            sentry_helpers.report_incident_to_sentry(
                RuntimeError("original"),
                "tag",
            )

    def test_ignores_none_context_values(self, monkeypatch):
        """Context avec valeur None ne doit pas creer de tag."""
        from app.core import sentry_helpers

        monkeypatch.setattr("app.core.config.settings.sentry_dsn", "https://fake@sentry.io/1")

        mock_sentry = MagicMock()
        mock_scope = MagicMock()
        mock_sentry.push_scope.return_value.__enter__.return_value = mock_scope
        mock_sentry.push_scope.return_value.__exit__.return_value = False

        with patch.dict("sys.modules", {"sentry_sdk": mock_sentry}):
            sentry_helpers.report_incident_to_sentry(
                RuntimeError("x"),
                "tag",
                valid_key="ok",
                skipped=None,
            )

        tag_calls = {call.args[0]: call.args[1] for call in mock_scope.set_tag.call_args_list}
        assert "valid_key" in tag_calls
        assert "skipped" not in tag_calls
