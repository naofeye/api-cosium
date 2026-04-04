"""Tests for RAG search module."""

import os
import tempfile
from unittest.mock import patch

from app.integrations.ai.rag import search_docs, _load_docs, _cache, DOCS_DIR


def _clear_cache():
    """Clear the module-level RAG cache between tests."""
    _cache.clear()


def test_search_docs_empty_query():
    """Empty query should return empty string (no keywords >= 3 chars)."""
    _clear_cache()
    result = search_docs("")
    assert result == ""


def test_search_docs_short_keywords():
    """Query with only short words (< 3 chars) returns empty."""
    _clear_cache()
    result = search_docs("ab cd")
    assert result == ""


def test_search_docs_no_docs_dir():
    """If docs directory doesn't exist, _load_docs returns empty dict."""
    _clear_cache()
    with patch("app.integrations.ai.rag.DOCS_DIR") as mock_dir:
        mock_dir.exists.return_value = False
        result = search_docs("monture progressif")
    assert result == ""


def test_search_docs_with_content():
    """Search should find relevant content from loaded documents."""
    _clear_cache()
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_path = os.path.join(tmpdir, "test_page.md")
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(
                "# Montures\n\n"
                "Les montures progressives sont disponibles en plusieurs modeles.\n"
                "Prix de 100 a 500 euros.\n"
            )

        from pathlib import Path

        with patch("app.integrations.ai.rag.DOCS_DIR", Path(tmpdir)):
            result = search_docs("monture progressif")

    assert "monture" in result.lower() or "progressi" in result.lower()


def test_search_docs_max_results():
    """Respects max_results parameter."""
    _clear_cache()
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(5):
            with open(os.path.join(tmpdir, f"doc_{i}.md"), "w", encoding="utf-8") as f:
                f.write(f"# Document {i}\n\nContenu avec le mot optique dans le document {i}.\n")

        from pathlib import Path

        with patch("app.integrations.ai.rag.DOCS_DIR", Path(tmpdir)):
            result = search_docs("optique", max_results=2)

    # Should contain at most 2 document sections
    assert result.count("---") <= 4  # 2 docs * 2 dashes each


def test_search_docs_max_chars():
    """Respects max_chars limit."""
    _clear_cache()
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "big.md"), "w", encoding="utf-8") as f:
            f.write("optique " * 2000)

        from pathlib import Path

        with patch("app.integrations.ai.rag.DOCS_DIR", Path(tmpdir)):
            result = search_docs("optique", max_chars=500)

    assert len(result) <= 600  # Allow some margin for header
