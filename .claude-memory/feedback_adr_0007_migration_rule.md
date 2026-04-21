---
name: Règle Alembic IF NOT EXISTS interdit (ADR 0007)
description: Toute nouvelle migration doit utiliser `op.create_table/add_column/create_index`. Le pattern `CREATE ... IF NOT EXISTS` est interdit, sauf pour la migration bootstrap `h3b4c5d6e7f8` documentée dans ADR 0007.
type: feedback
originSessionId: 78e8037f-0ea8-4de6-a636-c3826a097607
---
**Règle** : les migrations Alembic futures **doivent** utiliser l'API standard (`op.create_table`, `op.add_column`, `op.create_index`). **Aucun `CREATE TABLE IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS`** dans les migrations postérieures à `h3b4c5d6e7f8`.

**Why** : la migration `h3b4c5d6e7f8_add_cosium_reference_and_sync_tables.py` (21 tables Cosium, 463 L) utilise `IF NOT EXISTS` car elle rattrape un état de BDD divergent (`create_all()` pré-Alembic). Elle a été acceptée comme **bootstrap one-shot** via `docs/adr/0007-alembic-bootstrap-migration-accepted.md` (2026-04-18). Le problème : `IF NOT EXISTS` masque les divergences de schéma silencieusement + `alembic downgrade` devient irrécupérable + autogenerate Alembic ne fonctionne plus sur ces tables.

**How to apply** :
- En revue PR de toute nouvelle migration : grep pour `IF NOT EXISTS` dans les fichiers `alembic/versions/*.py` modifiés → rejeter si trouvé (sauf si c'est un fix ciblé sur `h3b4c5d6e7f8` lui-même).
- Si besoin de créer une table en tolérant un état divergent : utiliser `op.create_table` + catch `ProgrammingError` dans une migration de réconciliation explicite, **pas** `IF NOT EXISTS`.
- La docstring en tête de `h3b4c5d6e7f8_*.py` rappelle la règle avec pointeur vers ADR 0007.
