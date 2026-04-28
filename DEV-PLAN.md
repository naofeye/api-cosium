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
  Files: apps/api/app/api/routers/ai.py, apps/api/app/services/ai_service.py, apps/api/app/integrations/ai/claude_provider.py, apps/api/tests/test_ai.py
  Specs: ajouter POST /api/v1/ai/copilot/stream qui retourne un SSE avec les chunks Claude. Le service ai_service a déjà copilot_query() — ajouter copilot_stream() qui yield les chunks.
  Critères: endpoint retourne text/event-stream, chaque chunk est un event SSE, timeout 60s, tests avec mock Anthropic
  Niveau: 2

- [x] Copilot IA conversationnel — Frontend : page interactive _(fait 2026-04-27, commit `4e2e594`)_
  Files: apps/web/src/app/copilote-ia/page.tsx (remplacer le ComingSoon), apps/web/src/app/copilote-ia/components/ChatInterface.tsx (nouveau), apps/web/src/app/copilote-ia/components/MessageBubble.tsx (nouveau), apps/web/tests/pages/copilote-ia.test.tsx (nouveau)
  Specs: remplacer le stub ComingSoon par un vrai chat. Input en bas, messages qui scrollent, streaming SSE affiché en temps réel. 4 modes disponibles (dossier, financier, documentaire, marketing) via tabs ou dropdown.
  Critères: le chat fonctionne en streaming, les 4 modes sont sélectionnables, loading state pendant la réponse, historique en mémoire locale (pas persisté pour V1)
  Niveau: 2

- [x] Envoi devis par email au client _(fait 2026-04-28)_
  Files: apps/api/app/api/routers/devis.py, apps/api/app/services/devis_service.py, apps/api/app/integrations/email_sender.py, apps/api/app/repositories/devis_repo.py, apps/api/app/domain/schemas/devis.py, apps/api/app/templates/devis.html, apps/api/tests/test_devis.py, apps/web/src/app/devis/[id]/components/DevisActionButtons.tsx, apps/web/src/app/devis/[id]/components/DevisSendEmailDialog.tsx (nouveau), apps/web/src/app/devis/[id]/components/DevisTimeline.tsx, apps/web/tests/pages/devis-send-email.test.tsx (nouveau)
  Specs: ajouter POST /api/v1/devis/{id}/send-email (body: {to, subject?, message?}). Génère le PDF, attache au mail, envoie via EmailSender. Frontend : bouton "Envoyer par email" dans les actions du devis, dialog avec champ destinataire pré-rempli (email client).
  Critères: email envoyé avec PDF attaché, audit log, toast confirmation frontend, test backend avec mock SMTP
  Niveau: 2

- [ ] Envoi facture par email au client
  Files: apps/api/app/api/routers/factures.py, apps/api/app/services/facture_service.py, apps/api/app/integrations/email_sender.py, apps/web/src/app/factures/[id]/page.tsx
  Specs: même pattern que devis — POST /api/v1/factures/{id}/send-email. Bouton "Envoyer" sur la page détail facture.
  Critères: email envoyé avec PDF, audit log, toast, test
  Niveau: 2

### Priorité C — Manques fonctionnels

- [ ] Avoirs / notes de crédit sur factures
  Files: apps/api/app/api/routers/factures.py, apps/api/app/services/facture_service.py, apps/api/app/models/facture.py, apps/api/app/domain/schemas/factures.py, apps/api/app/repositories/facture_repo.py, apps/web/src/app/factures/[id]/page.tsx
  Specs: POST /api/v1/factures/{id}/avoir — crée une facture de type AVOIR liée à la facture originale. Montant négatif. Le modèle Facture a déjà un champ type mais pas de valeur AVOIR. Ajouter le type + la route + l'UI (bouton "Créer un avoir" sur la page facture).
  Critères: avoir créé avec lien vers facture originale, montant négatif, visible dans la liste factures avec badge "Avoir", PDF avec mention "AVOIR", test complet
  Niveau: 2

- [ ] Expiration automatique des devis
  Files: apps/api/app/models/devis.py, apps/api/app/services/devis_service.py, apps/api/app/tasks/*, apps/web/src/app/devis/page.tsx
  Specs: ajouter champ `expires_at` sur le modèle Devis (migration Alembic). Task Celery quotidienne qui passe les devis expirés en statut "expiré". Badge "Expiré" rouge dans la liste. Durée par défaut configurable (30 jours).
  Critères: migration, task Celery, badge UI, test service + test task
  Niveau: 2

- [ ] Historique conversationnel copilot IA (persisté)
  Files: apps/api/app/models/ai.py, apps/api/app/services/ai_service.py, apps/api/app/api/routers/ai.py, apps/api/app/repositories/ai_repo.py (nouveau)
  Specs: table `ai_conversations` (id, tenant_id, user_id, messages JSONB, created_at, updated_at). GET /api/v1/ai/conversations (liste), POST /api/v1/ai/conversations (créer), GET /api/v1/ai/conversations/{id} (reprendre). Le copilot_stream envoie l'historique comme contexte à Claude.
  Critères: conversations persistées, reprises, isolation tenant, migration, tests
  Niveau: 2

---

## En cours

*(rempli automatiquement par dev-cycle.sh)*

## Fait

*(déplacé ici après validation Nabil)*
