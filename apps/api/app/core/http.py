"""HTTP helpers : headers utilitaires pour reponses FastAPI."""

from __future__ import annotations

import re
from urllib.parse import quote

_ASCII_SAFE = re.compile(r"^[\x20-\x7e]+$")
_UNSAFE_CHARS = re.compile(r'[\r\n"\\]')


def content_disposition(filename: str, *, inline: bool = False) -> str:
    """Genere un header Content-Disposition conforme RFC 5987.

    Echappe les caracteres dangereux (CR/LF/guillemets) et fournit une version
    ASCII-safe (fallback) + une version UTF-8 encodee pour les filenames non-ASCII.
    """
    disposition = "inline" if inline else "attachment"
    safe = _UNSAFE_CHARS.sub("_", filename)
    if _ASCII_SAFE.match(safe):
        return f'{disposition}; filename="{safe}"'
    ascii_fallback = safe.encode("ascii", "replace").decode("ascii").replace("?", "_")
    encoded = quote(safe, safe="")
    return f"{disposition}; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"
