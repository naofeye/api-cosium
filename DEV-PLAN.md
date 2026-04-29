# DEV-PLAN.md — api-cosium (OptiFlow AI)

> Source de vérité pour le développement autonome.
> **Nabil** définit les priorités et les specs.
> **Les agents** (Claude + Codex) exécutent et rendent compte.
> Voir TODO.md pour le backlog complet — ce fichier ne contient que les items prêts à être implémentés.

## Direction (validée par Nabil 27/04/2026)

- **PAS de prod** pour l'instant (attente credentials API Cosium)
- **Priorité B** : polir ce qui existe (copilot IA, tests E2E, UX)
- **Priorité C** : combler les manques fonctionnels (avoirs, envoi devis, signature, SMS)

## Exigence qualité

Chaque feature implémentée doit être de **qualité professionnelle** :
- Backend : pattern router→service→repo, validation Pydantic, RBAC, tests unitaires, ruff vert
- Frontend : TypeScript strict (0 `any`), loading/error/empty states, responsive, accessibilité (aria-labels), vitest vert
- Pas de raccourci, pas de TODO laissé, pas de code mort

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

- [x] Déplacer seed_demo.py (435L) dans tests/factories/ _(fait 2026-04-26)_
- [x] Remplacer 15 `except Exception:` bare par `except Exception as e: logger.warning(...)` _(fait 2026-04-26)_
- [x] Ajouter `order_by` manquant sur `cosium_invoice_repo.first()` _(fait 2026-04-26)_
- [x] Split `ocr_service.py` _(déjà fait, facade 55L + handlers 132L + classification 158L)_
- [x] Coverage backend 45% → 55% : couvrir services non testés _(fait 2026-04-26)_

### P2 — Frontend qualité

- [ ] ESLint `no-explicit-any` warn → error
  Files: apps/web/.eslintrc.json, apps/web/eslint.config.* (+ fichiers .tsx/.ts avec `any`)
  Specs: passer la règle en error. Fixer les `any` restants.
  Critères: 0 erreur eslint, TS compile, vitest vert
  Niveau: 1
  ⚠️ ITEM LARGE — session interactive

---

### Priorité B — Polir ce qui existe

- [x] Copilot IA conversationnel — Backend : endpoint streaming SSE _(fait 2026-04-27, commit `4e2e594`)_
- [x] Copilot IA conversationnel — Frontend : page interactive _(fait 2026-04-27, commit `4e2e594`)_
- [x] Envoi devis par email au client _(fait 2026-04-28)_
- [x] Envoi facture par email au client _(fait 2026-04-28)_

### Priorité C — Manques fonctionnels

- [x] Avoirs / notes de crédit sur factures _(fait 2026-04-29 : modele original_facture_id + motif_avoir, migration c6f7g8h9i0j1, service create_avoir avec garde-fous, endpoint POST /factures/{id}/avoir, frontend CreateAvoirDialog + bandeau visuel. 8 tests verts.)_

- [x] Expiration automatique des devis _(fait 2026-04-29 : model valid_until + DEVIS_DEFAULT_VALIDITY_DAYS=90, migration b5e6f7g8h9i0 + backfill, task Celery beat 3h15 quotidien, frontend colonne couleur ambre J-7 / rouge expire. 6 tests verts.)_

- [x] Historique conversationnel copilot IA (persisté) _(fait 2026-04-29 : tables AiConversation + AiMessage avec FK CASCADE, migration d7g8h9i0j1k2, service append_message replay history, claude_provider accepte argument history, 4 endpoints CRUD, frontend HistoryPanel slide-in. 5 tests verts.)_

---

### P2 — Splits fichiers >400L

- [x] `analytics_cosium_extras.py` 481L → package 4 modules _(fait 2026-04-29)_
- [x] `sync.py` router 420L → package + orchestration dans service _(fait 2026-04-29)_
- [x] `main.py` 432L → 228L _(fait 2026-04-29)_
- [x] `tasks/sync_tasks.py` 440L → package par type _(fait 2026-04-29)_
- [x] `cosium_reference.py` router 401L → package _(fait 2026-04-29)_
- [x] `TabResume.tsx` 560L → 98L orchestrateur + `_resume/` package 7 fichiers _(fait 2026-04-29)_
- [x] `TabCosiumDocuments.tsx` 432L → 173L + `_cosium_documents/` package _(fait 2026-04-29)_
- [x] `apps/web/src/lib/hooks/use-api.ts` split par domaine _(fait 2026-04-29)_

### P1 — Splits fichiers >300L (audit 2026-04-29)

- [x] `ai_service.py` 445L → 122L + package `_ai/` _(fait 2026-04-29)_
- [x] `auth_service.py` 304L → 199L + package `_auth/` _(fait 2026-04-29)_
- [x] `client_import_service.py` 307L → 196L + `_client_import_helpers.py` _(fait 2026-04-29)_
- [x] `ChatInterface.tsx` 326L → 267L + `_chat/` _(fait 2026-04-29)_
- [x] `Header.tsx` 305L → 138L + `_header/NotificationsDropdown.tsx` _(fait 2026-04-29)_

---

## Prochains items candidats (P2/P3, à valider avec Nabil)

- [ ] ESLint strict : `no-explicit-any` + `exhaustive-deps` passer de `"warn"` → `"error"`
  Niveau: 1 — ⚠️ ITEM LARGE, session interactive

- [ ] RSC-first : audit systématique des `"use client"` inutiles (63% des .tsx)
  Niveau: 2 — checkpoint en fin

- [ ] CosiumClient injectable : factory + DI au lieu d'instance globale
  Niveau: 3 — validation AVANT de coder

- [ ] Avoirs : PDF avec mention "AVOIR" distincte (suite de C-1)
  Niveau: 1

---

## En cours

*(rempli automatiquement par dev-cycle.sh)*

## Fait

*(déplacé ici après validation Nabil)*
