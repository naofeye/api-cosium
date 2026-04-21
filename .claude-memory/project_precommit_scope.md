---
name: Pre-commit scope défensif uniquement
description: Les hooks actifs sont défensifs (sanity YAML/JSON/TOML + sécurité secrets). Les hooks réécriveurs (ruff-format, prettier, line-endings) sont désactivés — réécriraient 200+ fichiers legacy au 1er run.
type: project
originSessionId: 78e8037f-0ea8-4de6-a636-c3826a097607
---
**État** : `pip install pre-commit && pre-commit install` doit être fait une fois par clone. Hooks tournent automatiquement sur `git commit`.

**Hooks actifs** (`.pre-commit-config.yaml`) :
- `check-yaml --unsafe` (tolère `!reset` docker-compose)
- `check-json`, `check-toml`
- `check-merge-conflict`, `check-added-large-files` (500 kB max), `detect-private-key`
- `gitleaks` (tokens, API keys, credentials)

**Hooks désactivés** (commentés avec raison dans `.pre-commit-config.yaml`) :
- `ruff check --fix` + `ruff format` → réécrirait ~288 fichiers legacy
- `prettier` frontend → réécrirait ~193 fichiers
- `mixed-line-ending`, `end-of-file-fixer`, `trailing-whitespace` → ~800 fichiers CRLF→LF

**Commandes manuelles avant PR** (`CONTRIBUTING.md`) :
```bash
cd apps/api && python -m ruff check app/ --fix
cd apps/api && python -m ruff format app/
cd apps/web && npm run format
```

**Pour ré-activer** les hooks désactivés : faire un commit dédié de normalisation (`ruff format apps/api/app/` + `npm run format` + dos2unix sur le CRLF) puis dé-commenter les hooks dans `.pre-commit-config.yaml`.
