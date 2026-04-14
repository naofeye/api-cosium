#!/usr/bin/env python3
"""Genere un schema ERD textuel (Mermaid) depuis les modeles SQLAlchemy.

Usage : docker compose exec api python /app/scripts/generate_erd.py > docs/ERD.mmd
"""
import sys
from pathlib import Path

# Ajouter apps/api/app au PYTHONPATH si execute hors container
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.db.base import Base  # noqa: E402
import app.models  # noqa: F401, E402  -- charge tous les modeles


def generate_mermaid_erd() -> str:
    lines = ["erDiagram"]
    tables = sorted(Base.metadata.tables.values(), key=lambda t: t.name)
    for table in tables:
        lines.append(f"    {table.name} {{")
        for col in table.columns:
            col_type = type(col.type).__name__
            modifiers = []
            if col.primary_key:
                modifiers.append("PK")
            if col.foreign_keys:
                modifiers.append("FK")
            if not col.nullable:
                modifiers.append("NN")
            mod_str = " ".join(modifiers)
            lines.append(f"        {col_type} {col.name} {mod_str}".rstrip())
        lines.append("    }")
    # Foreign keys
    for table in tables:
        for col in table.columns:
            for fk in col.foreign_keys:
                target = fk.column.table.name
                lines.append(f"    {table.name} }}o--|| {target} : \"{col.name}\"")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(generate_mermaid_erd())
