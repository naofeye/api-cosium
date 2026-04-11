"""Tests for integrations/ai/claude_provider.py."""

from unittest.mock import MagicMock, patch

from app.integrations.ai.claude_provider import ClaudeProvider


class TestClaudeProviderNoKey:
    """Tests when no API key is configured."""

    def test_query_without_api_key_returns_placeholder(self):
        provider = ClaudeProvider()
        provider.api_key = ""
        result = provider.query("Bonjour")
        assert "[IA non configuree]" in result

    def test_query_with_usage_without_key_returns_zero_tokens(self):
        provider = ClaudeProvider()
        provider.api_key = ""
        result = provider.query_with_usage("Bonjour")
        assert result["tokens_in"] == 0
        assert result["tokens_out"] == 0
        assert "[IA non configuree]" in result["text"]
        assert "model" in result


class TestClaudeProviderWithKey:
    """Tests with mocked Anthropic API."""

    def _make_provider(self) -> ClaudeProvider:
        provider = ClaudeProvider()
        provider.api_key = "sk-test-fake-key"
        provider.model = "claude-haiku-4-5-20251001"
        return provider

    def _mock_response(self, text: str = "OK", tokens_in: int = 5, tokens_out: int = 5) -> MagicMock:
        resp = MagicMock()
        resp.content = [MagicMock(text=text)]
        resp.usage.input_tokens = tokens_in
        resp.usage.output_tokens = tokens_out
        return resp

    @patch("anthropic.Anthropic")
    def test_query_returns_text(self, mock_cls):
        mock_client = mock_cls.return_value
        mock_client.messages.create.return_value = self._mock_response("Reponse test", 10, 20)

        provider = self._make_provider()
        result = provider.query("Bonjour")
        assert result == "Reponse test"
        mock_client.messages.create.assert_called_once()

    @patch("anthropic.Anthropic")
    def test_query_with_usage_returns_dict(self, mock_cls):
        mock_client = mock_cls.return_value
        mock_client.messages.create.return_value = self._mock_response("Analyse du dossier", 50, 100)

        provider = self._make_provider()
        result = provider.query_with_usage("Analyse ce dossier", context="Contexte test")
        assert result["text"] == "Analyse du dossier"
        assert result["tokens_in"] == 50
        assert result["tokens_out"] == 100
        assert result["model"] == "claude-haiku-4-5-20251001"

    @patch("anthropic.Anthropic")
    def test_query_with_context_sends_extra_messages(self, mock_cls):
        mock_client = mock_cls.return_value
        mock_client.messages.create.return_value = self._mock_response()

        provider = self._make_provider()
        provider.query_with_usage("Question", context="Mon contexte")

        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        # With context: 2 context messages + 1 prompt = 3
        assert len(messages) == 3

    @patch("anthropic.Anthropic")
    def test_query_without_context_sends_one_message(self, mock_cls):
        mock_client = mock_cls.return_value
        mock_client.messages.create.return_value = self._mock_response()

        provider = self._make_provider()
        provider.query_with_usage("Question")

        call_args = mock_client.messages.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        assert len(messages) == 1

    @patch("anthropic.Anthropic")
    def test_api_error_returns_error_text(self, mock_cls):
        mock_client = mock_cls.return_value
        mock_client.messages.create.side_effect = Exception("API rate limit exceeded")

        provider = self._make_provider()
        result = provider.query_with_usage("Bonjour")
        assert "[Erreur IA]" in result["text"]
        assert result["tokens_in"] == 0
        assert result["tokens_out"] == 0

    @patch("anthropic.Anthropic")
    def test_query_error_returns_error_string(self, mock_cls):
        mock_client = mock_cls.return_value
        mock_client.messages.create.side_effect = RuntimeError("Connection failed")

        provider = self._make_provider()
        result = provider.query("Bonjour")
        assert "[Erreur IA]" in result
