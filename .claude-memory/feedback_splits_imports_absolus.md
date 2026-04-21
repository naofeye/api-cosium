---
name: Splits de package — imports absolus obligatoires
description: Quand on transforme un fichier mono en package Python splitte (xxx.py -> xxx/_sub.py), TOUTES les relations inter-modules doivent etre en imports absolus `from app.pkg.xxx._sub import ...`, jamais `from ._sub`.
type: feedback
originSessionId: 21e0df06-b2a4-4e95-bdf2-27568dbbb888
---
Quand on fait un split `xxx.py` → `xxx/{__init__.py, _sub.py, ...}`, utiliser des imports absolus partout (`from app.pkg.xxx._sub import ...`), **jamais** `from ._sub` ou `from . import _sub`.

**Why:** le test architectural `test_no_relative_imports_in_app` (charte CLAUDE.md "imports explicites uniquement") bloque tout `from .` / `from ..` dans `apps/api/app/`. Session 2026-04-18 a livré 5 splits backend qui sont tous passés sous le radar local et ont cassé la CI (3 runs rouges consecutifs, tests passed localement car ruff ne vérifie pas cette règle — seul pytest la vérifie). Corrige le 2026-04-19 via commits `a37b109` + `6e000e3`.

**How to apply:**
1. Pour chaque nouveau split de fichier en package : utiliser `from app.<chemin>.<pkg>.<sous-module> import ...` dans `__init__.py` ET dans chaque sous-module qui référence un pair (`_helpers.py`, etc.).
2. Ordre alpha strict (ruff I001) : `app.api.routers.sync._helpers` vient AVANT `app.core.*` (car `api < core` alphabétiquement).
3. Si du code externe patchait une référence via `@patch("app.pkg.xxx.symbol")`, après split le symbole peut avoir changé de module. Patcher le **vrai point d'usage** (ex: `app.pkg.xxx._helpers.symbol`) — ne pas re-exposer un alias dans `__init__` uniquement pour contenter le test, ça cache la dette.
4. Lancer `pytest tests/test_architecture.py` en local avant push — c'est un test statique rapide (<1s) qui ne nécessite pas Docker.
