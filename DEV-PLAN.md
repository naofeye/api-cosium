# DEV-PLAN.md — api-cosium (OptiFlow AI)

> Source de vérité pour le développement autonome.
> **Nabil** définit les priorités et les specs.
> **Les agents** (Claude + Codex) exécutent et rendent compte.
> Voir TODO.md pour le backlog complet — ce fichier ne contient que les items prêts à être implémentés.

## Règles

- Un seul item en cours à la fois
- Checkpoint Nabil obligatoire pour les items niveau 2+
- Max 15 min par item (timeout)
- Commit séparé par item (revert facile)
- NE PAS modifier les fichiers de config infra (docker-compose, .env, CI) sans validation
- Chaque item DOIT avoir un champ `Files:` qui liste les fichiers autorisés
- Claude ne peut modifier QUE les fichiers listés dans `Files:` — tout le reste est revert automatiquement
- Si un item est trop vague pour lister les fichiers → session interactive, pas dev-cycle

## Niveaux

- **Niveau 1** (safe) : fix bugs, ajouter tests, docs, refactor interne — pas de checkpoint
- **Niveau 2** (encadré) : nouvelle feature avec specs claires — checkpoint à la fin
- **Niveau 3** (créatif) : architecture, nouveau module — validation AVANT de coder

## Format d'un item

```
- [ ] Titre de la tâche
  Files: chemin/fichier1.py, chemin/fichier2.py (+ tests/nouveau_test.py si nouveau)
  Specs: description précise de ce qu'il faut faire
  Critères: comment vérifier que c'est bien fait
  Niveau: 1
```

---

## File d'attente

### P2 — Qualité

- [x] Déplacer seed_demo.py (435L) dans tests/factories/ _(fait 2026-04-26, 852s, ? fichiers)_
  Specs: extraire les fonctions de seed dans tests/factories/seed.py, garder un appel dans main.py si SEED_ON_STARTUP=true
  Critères: seed fonctionne toujours au démarrage, 0 régression tests, fichier < 200L
  Niveau: 1

- [x] Remplacer 15 `except Exception:` bare par `except Exception as e: logger.warning(...)` _(fait 2026-04-26, 270s, 6 fichiers)_
  Specs: fichiers concernés — admin_health.py, redis_cache.py, cosium_connector.py + les 12 autres occurrences
  Critères: chaque except log le contexte (fonction, paramètres), ruff vert, tests passent
  Niveau: 1

- [x] Ajouter `order_by` manquant sur `cosium_invoice_repo.first()` _(fait 2026-04-26, 241s, 2 fichiers)_
  Specs: cosium_invoice_repo.py:109, ajouter .order_by(CosiumInvoice.id) ou .order_by(CosiumInvoice.created_at.desc())
  Critères: pas de changement de comportement observable, test existant passe
  Niveau: 1

- [x] Split `ocr_service.py` _(déjà fait, facade 55L + handlers 132L + classification 158L)_ (383L) en `_ocr_handlers.py` (extracteurs) + `classification.py`
  Specs: garder l'interface publique identique, extraire les fonctions d'extraction par type de document
  Critères: imports publics inchangés, tests passent, chaque fichier < 200L
  Niveau: 1

- [x] Coverage backend 45% → 55% : couvrir services non testés _(fait 2026-04-26, 48s, ? fichiers)_
  Specs: identifier les services sans tests (grep -L "def test_" tests/), écrire des smoke tests pour chacun
  Critères: coverage monte de 10 points, 0 régression, pas de mock excessif
  Niveau: 1

### P2 — Frontend

- [ ] ESLint `no-explicit-any` warn → error
  Files: apps/web/.eslintrc.json, apps/web/eslint.config.* (+ tout fichier .tsx/.ts avec `any` à fixer)
  Specs: passer la règle en error dans la config. Fixer les `any` restants un par un.
  Critères: 0 erreur eslint, TS compile, vitest vert
  Niveau: 1
  ⚠️ ITEM LARGE — préférer session interactive (beaucoup de fichiers potentiels)

---

## En cours

*(rempli automatiquement par dev-cycle.sh)*

## Fait

*(déplacé ici après validation Nabil)*
