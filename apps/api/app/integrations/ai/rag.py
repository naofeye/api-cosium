"""RAG basique — recherche par mots-cles dans les docs Cosium."""

import re
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger("rag")

DOCS_DIR = Path("/app/docs/cosium/pages")
_cache: dict[str, str] = {}


def _load_docs() -> dict[str, str]:
    """Charge tous les fichiers markdown en memoire."""
    global _cache
    if _cache:
        return _cache

    if not DOCS_DIR.exists():
        logger.warning("rag_docs_dir_not_found", path=str(DOCS_DIR))
        return {}

    for f in DOCS_DIR.glob("*.md"):
        try:
            _cache[f.stem] = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

    logger.info("rag_docs_loaded", count=len(_cache))
    return _cache


def search_docs(query: str, max_results: int = 3, max_chars: int = 3000) -> str:
    """Recherche par mots-cles dans les docs Cosium.

    Retourne les passages les plus pertinents concatenes.
    """
    docs = _load_docs()
    if not docs:
        return ""

    keywords = re.findall(r"\w{3,}", query.lower())
    if not keywords:
        return ""

    scored: list[tuple[str, str, int]] = []
    for name, content in docs.items():
        lower_content = content.lower()
        score = sum(lower_content.count(kw) for kw in keywords)
        if score > 0:
            scored.append((name, content, score))

    scored.sort(key=lambda x: x[2], reverse=True)

    result_parts: list[str] = []
    total_chars = 0
    for name, content, _score in scored[:max_results]:
        # Extract relevant paragraphs
        paragraphs = content.split("\n\n")
        relevant = []
        for para in paragraphs:
            lower_para = para.lower()
            if any(kw in lower_para for kw in keywords):
                relevant.append(para.strip())

        if relevant:
            text = f"--- {name} ---\n" + "\n\n".join(relevant[:5])
        else:
            text = f"--- {name} ---\n" + content[:800]

        if total_chars + len(text) > max_chars:
            remaining = max_chars - total_chars
            if remaining > 100:
                result_parts.append(text[:remaining])
            break
        result_parts.append(text)
        total_chars += len(text)

    return "\n\n".join(result_parts)
