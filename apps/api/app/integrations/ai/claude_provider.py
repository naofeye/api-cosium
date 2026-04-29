"""Claude (Anthropic) AI provider implementation."""

from collections.abc import Iterator

from app.core.config import settings
from app.core.logging import get_logger
from app.integrations.ai.provider import AIProvider

logger = get_logger("claude_provider")

DEFAULT_SYSTEM = (
    "Tu es un assistant IA pour OptiFlow, une plateforme de gestion pour opticiens. "
    "Reponds en francais, de maniere concise et professionnelle."
)


class ClaudeProvider(AIProvider):
    """Implementation du provider IA avec l'API Anthropic Claude."""

    def __init__(self) -> None:
        self.api_key = settings.anthropic_api_key
        self.model = settings.ai_model

    def query(self, prompt: str, context: str = "", system: str = "") -> str:
        result = self.query_with_usage(prompt, context, system)
        return result["text"]

    def query_with_usage(
        self,
        prompt: str,
        context: str = "",
        system: str = "",
        history: list[dict] | None = None,
    ) -> dict:
        """Query Claude. `history` (optionnel) = liste de messages [{role, content}, ...]
        precedents (sans le prompt courant). Le prompt est ajoute en dernier message user.
        """
        if not self.api_key:
            return {
                "text": "[IA non configuree] Ajoutez ANTHROPIC_API_KEY dans votre fichier .env pour activer l'assistant IA.",
                "tokens_in": 0,
                "tokens_out": 0,
                "model": self.model,
            }

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key)

            messages = []
            if context:
                messages.append({"role": "user", "content": f"Voici le contexte :\n\n{context}"})
                messages.append(
                    {
                        "role": "assistant",
                        "content": "J'ai bien pris en compte le contexte. Quelle est votre question ?",
                    }
                )

            # Replay de l'historique conversationnel
            if history:
                messages.extend(history)

            messages.append({"role": "user", "content": prompt})

            response = client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system or DEFAULT_SYSTEM,
                messages=messages,
            )

            result = response.content[0].text
            tokens_in = getattr(response.usage, "input_tokens", 0)
            tokens_out = getattr(response.usage, "output_tokens", 0)
            logger.info(
                "claude_query_success",
                prompt_len=len(prompt),
                response_len=len(result),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )
            return {"text": result, "tokens_in": tokens_in, "tokens_out": tokens_out, "model": self.model}

        except Exception as e:
            logger.error("claude_query_failed", error=str(e))
            return {"text": "[Erreur IA] Une erreur est survenue lors de la requete IA. Veuillez reessayer.", "tokens_in": 0, "tokens_out": 0, "model": self.model}

    def query_stream(
        self, prompt: str, context: str = "", system: str = ""
    ) -> Iterator[dict]:
        """Stream une reponse Claude par chunks.

        Yields des dicts de la forme :
        - {"type": "chunk", "text": "..."} pour chaque morceau de texte
        - {"type": "done", "tokens_in": int, "tokens_out": int, "model": str} a la fin
        - {"type": "error", "error": str} en cas d'echec (a la place de "done")
        """
        if not self.api_key:
            yield {
                "type": "chunk",
                "text": "[IA non configuree] Ajoutez ANTHROPIC_API_KEY dans votre fichier .env pour activer l'assistant IA.",
            }
            yield {"type": "done", "tokens_in": 0, "tokens_out": 0, "model": self.model}
            return

        try:
            import anthropic

            client = anthropic.Anthropic(api_key=self.api_key, timeout=60.0)

            messages: list[dict[str, str]] = []
            if context:
                messages.append({"role": "user", "content": f"Voici le contexte :\n\n{context}"})
                messages.append(
                    {
                        "role": "assistant",
                        "content": "J'ai bien pris en compte le contexte. Quelle est votre question ?",
                    }
                )
            messages.append({"role": "user", "content": prompt})

            with client.messages.stream(
                model=self.model,
                max_tokens=2048,
                system=system or DEFAULT_SYSTEM,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    if text:
                        yield {"type": "chunk", "text": text}
                final = stream.get_final_message()

            tokens_in = getattr(final.usage, "input_tokens", 0)
            tokens_out = getattr(final.usage, "output_tokens", 0)
            logger.info(
                "claude_stream_success",
                prompt_len=len(prompt),
                tokens_in=tokens_in,
                tokens_out=tokens_out,
            )
            yield {
                "type": "done",
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "model": self.model,
            }

        except Exception as e:
            logger.error("claude_stream_failed", error=str(e))
            yield {
                "type": "error",
                "error": "[Erreur IA] Une erreur est survenue lors de la requete IA. Veuillez reessayer.",
            }


claude_provider = ClaudeProvider()
