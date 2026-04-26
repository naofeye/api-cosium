# DEV-PLAN.md — api-cosium (OptiFlow AI)

> Source de vérité pour le développement autonome.
> **Nabil** définit les priorités et les specs.
> **Les agents** (Claude + Codex) exécutent et rendent compte.
> Voir TODO.md pour le backlog complet — ce fichier ne contient que les items prêts à être implémentés.

## Règles

- Un seul item en cours à la fois
- Checkpoint Nabil obligatoire pour les items niveau 2+
- Max 30 min par item (timeout)
- Commit séparé par item (revert facile)
- NE PAS modifier les fichiers de config infra (docker-compose, .env, CI) sans validation
- Suivre les patterns du CLAUDE.md (router→service→repo, Pydantic schemas, etc.)

## Niveaux

- **Niveau 1** (safe) : fix bugs, ajouter tests, docs, refactor interne — pas de checkpoint
- **Niveau 2** (encadré) : nouvelle feature avec specs claires — checkpoint à la fin
- **Niveau 3** (créatif) : architecture, nouveau module — validation AVANT de coder

---

## File d'attente

### P2 — Qualité

- [x] Déplacer seed_demo.py (435L) dans tests/factories/ _(fait 2026-04-26, 852s, ? fichiers)_
  Specs: extraire les fonctions de seed dans tests/factories/seed.py, garder un appel dans main.py si SEED_ON_STARTUP=true
  Critères: seed fonctionne toujours au démarrage, 0 régression tests, fichier < 200L
  Niveau: 1

- [ ] Remplacer 15 `except Exception:` bare par `except Exception as e: logger.warning(...)`
  Specs: fichiers concernés — admin_health.py, redis_cache.py, cosium_connector.py + les 12 autres occurrences
  Critères: chaque except log le contexte (fonction, paramètres), ruff vert, tests passent
  Niveau: 1

- [ ] Ajouter `order_by` manquant sur `cosium_invoice_repo.first()`
  Specs: cosium_invoice_repo.py:109, ajouter .order_by(CosiumInvoice.id) ou .order_by(CosiumInvoice.created_at.desc())
  Critères: pas de changement de comportement observable, test existant passe
  Niveau: 1

- [ ] Split `ocr_service.py` (383L) en `_ocr_handlers.py` (extracteurs) + `classification.py`
  Specs: garder l'interface publique identique, extraire les fonctions d'extraction par type de document
  Critères: imports publics inchangés, tests passent, chaque fichier < 200L
  Niveau: 1

- [ ] Coverage backend 45% → 55% : couvrir services non testés
  Specs: identifier les services sans tests (grep -L "def test_" tests/), écrire des smoke tests pour chacun
  Critères: coverage monte de 10 points, 0 régression, pas de mock excessif
  Niveau: 1

### P2 — Frontend

- [ ] ESLint `no-explicit-any` warn → error
  Specs: dans .eslintrc ou eslint.config, passer la règle en error. Fixer les any restants.
  Critères: 0 erreur eslint, TS compile, vitest vert
  Niveau: 1

---

## En cours

*(rempli automatiquement par dev-cycle.sh)*

## Fait

*(déplacé ici après validation Nabil)*
