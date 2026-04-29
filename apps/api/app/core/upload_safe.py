"""Helper d'upload chunked avec limite RAM.

Empeche un client authentifie d'envoyer un multipart enorme (1 GB+) qui
serait charge en RAM avant validation. Pattern aligne avec
`apps/api/app/api/routers/documents.py`.
"""

from fastapi import Request, UploadFile

from app.core.config import settings
from app.core.exceptions import ValidationError

UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MB


async def read_upload_safely(file: UploadFile, request: Request, max_mb: int | None = None) -> bytes:
    """Lit un UploadFile par chunks en bornant la taille totale.

    - Pre-check Content-Length pour rejeter sans rien lire les requetes
      evidemment trop grosses.
    - Lecture par chunks avec arret anticipe pour eviter le DoS memoire.

    Args:
        file: UploadFile FastAPI.
        request: Request (utilise pour lire Content-Length).
        max_mb: Plafond en MB. Defaut = settings.max_upload_size_mb.

    Returns:
        bytes (contenu complet du fichier).

    Raises:
        ValidationError si le fichier depasse la limite.
    """
    limit_mb = max_mb if max_mb is not None else settings.max_upload_size_mb
    max_size = limit_mb * 1024 * 1024

    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > max_size + UPLOAD_CHUNK_SIZE:
        raise ValidationError("file", f"Fichier trop volumineux (max {limit_mb} MB)")

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            raise ValidationError("file", f"Fichier trop volumineux (max {limit_mb} MB)")
        chunks.append(chunk)
    return b"".join(chunks)
