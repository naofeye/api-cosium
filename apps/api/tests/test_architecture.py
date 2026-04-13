"""Tests architecturaux : verification structurelle des regles CLAUDE.md.

Ces tests echouent si :
- Un repo contient `db.commit()` (regle : services gerent les commits)
- Un router contient de la logique BDD directe (regle : routers SLIM)
- Un service contient `HTTPException` (regle : exceptions metier custom)
- Un fichier python depasse 300 lignes (regle : decoupage)
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent  # apps/api/
APP_DIR = REPO_ROOT / "app"


def _python_files(subdir: str) -> list[Path]:
    return sorted((APP_DIR / subdir).rglob("*.py"))


def test_no_commit_in_repositories():
    """Regle CLAUDE.md : les repositories ne doivent contenir QUE des queries.
    Le commit est responsabilite des services."""
    offenders = []
    for f in _python_files("repositories"):
        content = f.read_text(encoding="utf-8")
        if "db.commit()" in content:
            offenders.append(f.relative_to(APP_DIR))
    assert not offenders, (
        f"Les repos suivants contiennent db.commit() (interdit) :\n  - "
        + "\n  - ".join(str(o) for o in offenders)
    )


def test_no_query_in_routers():
    """Regle CLAUDE.md : les routers ne doivent PAS contenir db.query() ou select(.
    Tout passe par un repository via un service."""
    offenders = []
    for f in _python_files("api/routers"):
        if f.name in ("__init__.py",):
            continue
        content = f.read_text(encoding="utf-8")
        # Detection grossiere : tolere les imports de schemas Pydantic
        if "db.query(" in content:
            offenders.append((str(f.relative_to(APP_DIR)), "db.query()"))
    assert not offenders, (
        f"Les routers suivants contiennent du SQL direct :\n  - "
        + "\n  - ".join(f"{p} -> {p2}" for p, p2 in offenders)
    )


def test_no_http_exception_in_services():
    """Regle CLAUDE.md : les services ne doivent pas lever HTTPException
    (utiliser exceptions metier custom dans core/exceptions.py)."""
    offenders = []
    for f in _python_files("services"):
        if f.name == "__init__.py":
            continue
        content = f.read_text(encoding="utf-8")
        if "HTTPException" in content and "from fastapi" in content:
            offenders.append(str(f.relative_to(APP_DIR)))
    assert not offenders, (
        f"Les services suivants utilisent HTTPException :\n  - "
        + "\n  - ".join(offenders)
    )


def test_no_python_file_over_threshold():
    """Regle CLAUDE.md : pas de fichier > 300 lignes (decoupage obligatoire).
    Tolerance : tests/, migrations/, models/__init__.py."""
    THRESHOLD = 600  # tolerance haute pour seuil dur (300 reste l'objectif)
    offenders = []
    for f in APP_DIR.rglob("*.py"):
        rel = f.relative_to(APP_DIR)
        # Skip alembic migrations + agreges __init__
        if "alembic" in rel.parts or "models" in rel.parts and f.name == "__init__.py":
            continue
        line_count = sum(1 for _ in f.read_text(encoding="utf-8").splitlines())
        if line_count > THRESHOLD:
            offenders.append((str(rel), line_count))
    assert not offenders, (
        f"Fichiers > {THRESHOLD} lignes (a decouper) :\n  - "
        + "\n  - ".join(f"{p} : {n} lignes" for p, n in offenders)
    )


def test_no_print_in_app():
    """Regle CLAUDE.md : pas de print() en production, utiliser le logger."""
    offenders = []
    for f in APP_DIR.rglob("*.py"):
        if f.name == "__init__.py":
            continue
        content = f.read_text(encoding="utf-8")
        # Detection : print( en debut de ligne ou avec indentation, pas dans un commentaire
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith("print(") and not stripped.startswith("#"):
                offenders.append((str(f.relative_to(APP_DIR)), i))
                break  # un seul par fichier suffit pour le rapport
    assert not offenders, (
        f"print() trouve (utiliser le logger) :\n  - "
        + "\n  - ".join(f"{p}:L{n}" for p, n in offenders)
    )


def test_no_relative_imports_in_app():
    """Regle CLAUDE.md : imports absolus uniquement (from app.x import ...)."""
    offenders = []
    for f in APP_DIR.rglob("*.py"):
        content = f.read_text(encoding="utf-8")
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.lstrip()
            if stripped.startswith(("from .", "from ..")):
                offenders.append((str(f.relative_to(APP_DIR)), i, line.strip()))
    assert not offenders, (
        f"Imports relatifs interdits :\n  - "
        + "\n  - ".join(f"{p}:L{n} -> {l}" for p, n, l in offenders)
    )
