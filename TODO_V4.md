# TODO V4 — OptiFlow AI — Audit avec regard neuf (subtilites)

> **Date** : 2026-04-07
> **Contexte** : 4e audit — focus sur les bugs subtils que les 3 audits precedents ont manque
> **Methode** : Analyse de race conditions, precision financiere, securite avancee, architecture
> **Regle** : Cocher `[x]` quand termine.

---

## PHASE 1 — CRITIQUE : PRECISION FINANCIERE (Semaine 1)
> float vs Decimal — risque de centimes manquants sur TOUTES les operations financieres

### 1.1 Modeles SQLAlchemy : float → Decimal [CRITIQUE]
- [ ] `models/payment.py` — Changer `Mapped[float]` en `Mapped[Decimal]` pour `amount_due`, `amount_paid` (colonnes Numeric(10,2))
- [ ] `models/devis.py` — Idem pour `montant_ht`, `tva`, `montant_ttc`, `part_secu`, `part_mutuelle`, `reste_a_charge`
- [ ] `models/facture.py` — Idem pour tous les montants
- [ ] `models/devis.py` (DevisLigne) — Idem pour `prix_unitaire_ht`, `montant_ht`, `montant_ttc`
- [ ] `models/pec.py` (PecRequest) — Idem pour `montant_demande`, `montant_accorde`
- [ ] `models/bank_transaction.py` — Idem pour `montant`
- [ ] Ajouter `from decimal import Decimal` dans chaque fichier modifie

### 1.2 Services : calculs financiers en Decimal [CRITIQUE]
- [ ] `services/analytics_kpi_service.py` — Remplacer `float(r.amount_due)` par `Decimal(str(r.amount_due))` dans les calculs KPI
- [ ] `services/reconciliation_service.py` — Idem pour les calculs de rapprochement
- [ ] Rechercher `float(` dans tous les services et remplacer par Decimal la ou c'est financier

---

## PHASE 2 — CRITIQUE : RACE CONDITIONS (Semaine 1)
> Merge clients sans lock = corruption de donnees possible

### 2.1 Lock sur le merge clients [CRITIQUE]
- [ ] `api/routers/clients.py` — Ajouter `acquire_lock(f"merge:{tenant_id}:{keep_id}:{merge_id}", ttl=60)` avant d'appeler `merge_clients()`
- [ ] Ajouter `release_lock()` dans un `finally` block

### 2.2 Sync error propagation [ELEVE]
- [ ] `api/routers/sync.py:234-280` — Quand `has_errors=True`, retourner HTTP 207 (Multi-Status) au lieu de 200
- [ ] Ou alternativement, ajouter un champ `"success": false` explicite dans la reponse

---

## PHASE 3 — ELEVE : SECURITE AVANCEE (Semaine 1-2)

### 3.1 Email header injection [ELEVE]
- [ ] `tasks/reminder_tasks.py` — Sanitiser le subject email avec `re.sub(r'[\r\n\t]', ' ', subject)` avant envoi

### 3.2 Repo get_by_id retourne les clients supprimes [ELEVE]
- [ ] `repositories/client_repo.py` — `get_by_id()` doit filtrer `deleted_at IS NULL` par defaut (comme `get_by_id_active`)
- [ ] Renommer l'ancien `get_by_id()` en `get_by_id_including_deleted()` pour les cas ou c'est necessaire (restore, admin)
- [ ] Mettre a jour tous les appelants qui utilisaient `get_by_id()` (12 services)

### 3.3 deleted_at expose dans l'API [MOYEN]
- [ ] `domain/schemas/clients.py` — Retirer `deleted_at` du schema `ClientResponse` (visible uniquement dans un schema admin)

---

## PHASE 4 — ELEVE : FRONTEND SUBTILITES (Semaine 2)

### 4.1 InlineEdit memory leak [ELEVE]
- [ ] `components/ui/InlineEdit.tsx` — Le `setTimeout` dans `onBlur` n'est pas nettoye si le composant se demonte → ajouter cleanup useEffect

### 4.2 Token refresh timeout race [ELEVE]
- [ ] `lib/api.ts` — Le timeout AbortController du premier appel n'est pas annule lors du retry apres refresh → clearTimeout avant retry

### 4.3 SSE reconnexion hang [ELEVE]
- [ ] `lib/sse.ts` — La reconnexion peut bloquer si `onerror` fire plusieurs fois rapidement → verifier que eventSource est bien null avant reconnect

### 4.4 Popstate navigation trap [ELEVE]
- [ ] `hooks/useUnsavedChangesWarning.ts` — `e.preventDefault()` est un no-op sur popstate → corriger le back button loop

### 4.5 SWR deduping masque les mutations [MOYEN]
- [ ] `lib/swr.tsx` — Reduire `dedupingInterval` de 5000ms a 2000ms pour que les creations apparaissent plus vite

### 4.6 useTransition pending non reset [MOYEN]
- [ ] `clients/page.tsx` — Si la recherche de doublons echoue, `dupesPending` reste `true` indefiniment → reset dans le catch

### 4.7 Keyboard shortcuts force reload [MOYEN]
- [ ] `lib/shortcuts.ts` — `window.location.href` navigations → remplacer par `router.push()` pour eviter le rechargement complet

### 4.8 TenantSelector focus trap [FAIBLE]
- [ ] `components/layout/TenantSelector.tsx` — Ajouter fermeture avec Escape et gestion pointer events

---

## PHASE 5 — MOYEN : CONFIGURATION ET ARCHITECTURE (Semaine 2-3)

### 5.1 Variables d'environnement non documentees [MOYEN]
- [ ] `backend/app/db/session.py:9` — `CELERY_WORKER` utilise via `os.environ` au lieu de Settings → migrer dans config.py
- [ ] `backend/app/main.py:180` — `SEED_ON_STARTUP` utilise via `os.environ` → migrer dans config.py
- [ ] `.env.example` — Ajouter `CELERY_WORKER=` et `SEED_ON_STARTUP=true` avec commentaires

### 5.2 Transaction per-document dans cosium_document_sync [MOYEN]
- [ ] `services/cosium_document_sync.py:140-146` — Deplacer `db.commit()` hors de la boucle (batched commit)
- [ ] Ajouter compensation si MinIO upload echoue apres db.add()

### 5.3 Export sans tenant context [MOYEN]
- [ ] `clients/page.tsx:50` — `window.open()` pour export ne passe pas de tenant context explicite → verifier que le cookie est bien envoye

---

## PHASE 6 — FAIBLE : AMELIORATIONS (Ongoing)

### 6.1 Tests et validation Docker [FAIBLE]
- [ ] Tester deploiement E2E avec docker-compose.prod.yml
- [ ] Tester TLS de bout en bout
- [ ] Tester cycle backup → restore
- [ ] Tester multi-tenant parallele
- [ ] Tester sync Cosium realiste
- [ ] Profiler endpoints les plus lents

### 6.2 Monitoring [FAIBLE]
- [ ] Endpoint `/metrics` Prometheus-compatible
- [ ] Monitorer temps de reponse
- [ ] Monitorer queue Celery
- [ ] Alertes 5xx
- [ ] Slow query logging (> 1s)

### 6.3 Frontend polish [FAIBLE]
- [ ] TypeScript types auto-generes depuis OpenAPI (openapi-typescript)
- [ ] Chart error boundaries supplementaires (statistiques page)
- [ ] DataTable localStorage race condition multi-tab

---

## SUIVI GLOBAL

| Phase | Description | Taches | Priorite |
|-------|-------------|--------|----------|
| Phase 1 | Precision financiere (float→Decimal) | 10 | CRITIQUE |
| Phase 2 | Race conditions (merge lock, sync errors) | 3 | CRITIQUE |
| Phase 3 | Securite avancee (email, soft-delete, API) | 4 | ELEVE |
| Phase 4 | Frontend subtilites | 8 | ELEVE/MOYEN |
| Phase 5 | Configuration et architecture | 5 | MOYEN |
| Phase 6 | Tests Docker + monitoring + polish | 14 | FAIBLE |
| **TOTAL** | | **44** | |

---

## CE QUE L'AUDIT V4 A TROUVE QUE LES 3 PRECEDENTS ONT RATE

1. **float vs Decimal** — TOUS les montants financiers sont en `float` dans les modeles alors que les colonnes sont `Numeric(10,2)`. Risque de centimes manquants sur les calculs cumules.
2. **Race condition merge** — Le merge clients n'a aucun lock distribue (contrairement au sync qui en a un).
3. **Email header injection** — Le subject des emails de relance n'est pas sanitise contre les `\r\n`.
4. **get_by_id retourne les clients supprimes** — 12 services appellent `get_by_id()` qui ne filtre PAS `deleted_at`.
5. **InlineEdit setTimeout memory leak** — Chaque blur d'un champ inline cree un setTimeout non nettoye.
6. **Popstate back button trap** — `preventDefault()` est un no-op sur popstate, cree une boucle infinie.
7. **Token refresh timeout race** — Le AbortController du premier appel n'est pas annule au retry.
8. **Per-document commit dans cosium_document_sync** — Commit dans la boucle au lieu de batch.
9. **Env vars non dans Settings** — `CELERY_WORKER` et `SEED_ON_STARTUP` echappent a Pydantic.
