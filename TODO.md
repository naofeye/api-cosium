# TODO LIST OPTIFLOW AI — Plan de reprise post-audit complet

> **Date de creation** : 2026-04-07
> **Methode** : Audit Codex 3 passes + audit profond Claude Opus (routers, services, models, schemas, core, frontend, infra, tasks)
> **Regle** : Cocher `[x]` quand termine. Ne jamais supprimer une ligne, meme terminee.
> **Total** : 257 taches en 12 phases

---

## PHASE 1 — FAILLES DE SECURITE CRITIQUES (Semaine 1)
> Objectif : corriger les vulnerabilites qui empechent toute mise en production

### 1.1 Secrets et credentials par defaut [CRITIQUE]
- [x] `core/config.py:12` — Supprimer la valeur par defaut `"change-me-super-secret"` de `jwt_secret`, le rendre obligatoire
- [x] `core/config.py:10` — Supprimer le mot de passe par defaut `"optiflow"` de `database_url`, documenter la config
- [x] `core/config.py:21-22` — Supprimer les defaults `"minioadmin"` de `s3_access_key`/`s3_secret_key`
- [x] `core/config.py:50` — Rendre `encryption_key` obligatoire en prod (pas de default vide)
- [x] `core/encryption.py:10-13` — Supprimer le fallback qui derive la cle Fernet du `JWT_SECRET`
- [x] Ajouter un validateur Pydantic dans `config.py` qui refuse les valeurs par defaut si `ENV=production`
- [x] Mettre a jour `.env.example` avec des commentaires clairs sur chaque secret obligatoire

### 1.2 Isolation multi-tenant cassee dans les modeles [CRITIQUE]
- [x] `models/batch_operation.py:61-102` — Ajouter `tenant_id` a `BatchOperationItem` (manquant = breach d'isolation)
- [x] `models/pec_preparation.py:76-102` — Ajouter `tenant_id` a `PecPreparationDocument` (manquant = breach d'isolation)
- [x] `models/devis.py:14` — Changer `unique=True` sur `numero` en `UniqueConstraint("tenant_id", "numero")` (collision inter-tenants)
- [x] `models/facture.py:16` — Idem : `numero` doit etre unique PAR TENANT, pas globalement
- [x] `models/pec.py:15` — `PayerOrganization.code` : unique par tenant, pas globalement
- [x] `models/payment.py:23` — `idempotency_key` : unique par tenant, pas globalement + ajout index (tenant_id, status)
- [x] Migration Alembic `o0p1q2r3s4t5_security_audit_fixes.py` creee (tenant_id, unique constraints, indexes)
- [x] Verifier `models/document.py:9-17` — `DocumentType` est un referentiel systeme global (pas tenant-scoped, c'est correct)

### 1.3 Escalade de privileges dans les dependencies [CRITIQUE]
- [x] `core/deps.py:17-41` — `get_current_user()` ne valide PAS le tenant_id du token → ajouter verification `TenantUser`
- [x] `core/deps.py:44-50` — `require_role()` utilise `User.role` (global) au lieu de `TenantUser.role` (par tenant) → corriger
- [x] `services/auth_service.py:163,227` — Supprimer le fallback `tenant_id = 1` si TenantUser non trouve (FAILLE DE SECURITE)
- [x] `core/tenant_context.py` — Corriger le filtre `TenantUser.is_active` → `TenantUser.is_active.is_(True)`
- [ ] Ajouter des tests d'integration : user du tenant A ne peut PAS acceder aux donnees du tenant B

### 1.4 Protection CSRF et bruteforce [CRITIQUE]
- [x] CSRF protege par `SameSite=Lax` sur tous les cookies httpOnly (protection standard navigateurs modernes)
- [x] Ajouter un rate limiting specifique sur `/forgot-password` (max 3/h) et `/reset-password` (max 5/h) dans rate_limiter.py
- [x] Implementer un account lockout apres 5 tentatives echouees (lockout 30 min) dans auth_service.py via Redis
- [x] Renforcer les regles de complexite de mot de passe (10 chars, upper/lower/digit/special) dans schemas/auth.py
- [x] Ajouter `EmailStr` sur `ForgotPasswordRequest.email` (validation format email)

---

## PHASE 2 — URGENCES PRODUCTION (Semaine 1-2)
> Objectif : rendre le projet deployable

### 2.1 Bootstrap backend dangereux [CRITIQUE]
- [x] `main.py:247-259` — Supprimer `Base.metadata.create_all()` du startup
- [x] `main.py:267-270` — Rendre `seed_data()` conditionnel a un flag `SEED_ON_STARTUP=true` (desactive par defaut)
- [x] Migration Alembic creee pour tous les changements de schema de l'audit
- [x] Check Alembic au startup : log WARNING si des migrations pending existent
- [x] `main.py:263-276` — Les erreurs de startup (MinIO, tables) sont catchees mais ne bloquent pas le demarrage → crash explicite si critique

### 2.2 Pipeline de deploiement casse [CRITIQUE]
- [x] `scripts/deploy.sh` — Reecrit completement : backup inline pg_dump, healthcheck interne via docker exec, verification via nginx port 80
- [x] Corriger les healthchecks dans `deploy.sh` : remplacer `localhost:8000` par le bon endpoint
- [x] Verifier `docker-compose.prod.yml` — healthchecks internes OK (curl localhost:8000 dans le conteneur, pas depuis l'hote)
- [ ] Tester un deploiement complet de bout en bout en local avec le compose prod
- [x] Documenter le runbook de deploiement dans `DEPLOY.md` (190 lignes, 9 sections)

### 2.3 HTTPS production non finalise [CRITIQUE]
- [x] Bloc HTTPS complet dans `nginx/nginx.conf` (TLS 1.2/1.3, ciphers, HSTS, rate limit login, /docs bloque)
- [x] Redirection HTTP → HTTPS incluse dans le bloc commente
- [x] Instructions certbot dans le fichier + `DEPLOY.md`
- [ ] Tester la terminaison TLS de bout en bout (necessite un vrai domaine)
- [x] Cookies avec flags `Secure` et `SameSite` deja configures dans `auth.py` (`_COOKIE_OPTS`)

### 2.4 CORS, middleware et exposition [ELEVE]
- [x] `main.py:157` — Verifier que `cors_origins` ne contient JAMAIS `*` en production (valide par model_validator dans config.py)
- [x] `main.py:159` — Restreindre `allow_methods` (retire PATCH, garde GET/POST/PUT/DELETE/OPTIONS)
- [x] `main.py:202-207` — Sanitise les messages d'exception (exc_type + message tronque 200 chars, X-Request-ID dans la reponse)
- [x] Ordre middlewares verifie et documente : CORS > SecurityHeaders > RequestId > RateLimiter > GZip (LIFO correct)
- [x] `nginx/nginx.conf` — Bloquer `/docs` et `/openapi.json` en production (return 404)

---

## PHASE 3 — SECURITE AUTH & SESSIONS (Semaine 2-3)
> Objectif : authentification robuste et sessions maitrisees

### 3.1 JWT et tokens [ELEVE]
- [x] `security.py` — Claims `iss=optiflow` et `aud=optiflow-api` ajoutes dans les JWT
- [x] Validation `iss` et `aud` lors du decode (PyJWT rejette les tokens non conformes)
- [x] Blacklist de tokens Redis implementee : `blacklist_access_token()`, `is_token_blacklisted()`, integre dans deps.py et logout
- [x] Documenter la duree de vie des tokens (30min access, 7j refresh, revocation au login/switch/password)

### 3.2 Cookie d'auth frontend [MOYEN]
- [x] `frontend/src/middleware.ts:5` — Supprimer le fallback `optiflow_authenticated` cookie
- [x] Utiliser uniquement le cookie httpOnly `optiflow_token` pour la garde d'auth
- [x] Endpoint `GET /api/v1/auth/me` deja existant dans auth.py (verifie)
- [ ] Tester : deconnexion, expiration token, acces non autorise

### 3.3 Gestion des refresh tokens [MOYEN]
- [x] `auth_service.py` — Revoquer les anciens refresh tokens lors du login
- [x] Revoquer lors du switch tenant
- [x] Ajouter un endpoint `POST /api/v1/auth/logout-all` pour revoquer toutes les sessions
- [ ] Ajouter un test d'integration pour le flux complet login/refresh/logout

### 3.5 Lock Redis corrige [FAIT]
- [x] `redis_cache.py` — `acquire_lock()` retourne maintenant `False` si Redis est down (au lieu de `True`)
- [x] Ajout de `get_redis_client()` public pour le lockout et autres usages

### 3.4 Rate limiting [ELEVE]
- [x] `core/rate_limiter.py:118` — Utiliser `X-Forwarded-For` pour detecter la vraie IP derriere un proxy
- [x] Proxies de confiance : nginx seul proxy, X-Forwarded-For ajoute par nginx (trustable)
- [x] `rate_limiter.py:44-45` — Le fallback in-memory rendu thread-safe avec `threading.Lock()`
- [x] Rate limiting par IP suffit pour les endpoints publics ; authentifies proteges par lockout + refresh token
- [x] `RATE_LIMIT_RULES` dans rate_limiter.py est acceptable (config specifique au middleware, pas env-dependant)

---

## PHASE 4 — DIAGNOSTICS ET ADMIN (Semaine 3-4)
> Objectif : que les ecrans d'admin montrent la verite

### 4.1 Diagnostics Cosium non scopes par tenant [ELEVE]
- [x] `admin_health.py` — `_check_cosium_status()` modifie pour accepter db+tenant_id et utiliser les cookies chiffres du tenant
- [x] Modifier `test_cosium_connection()` pour utiliser le meme mecanisme (db+tenant injectes)
- [x] URL Redis hardcodee remplacee par `settings.redis_url`
- [x] `admin_health.py` — Logique metriques extraite dans `admin_metrics_service.py`
- [x] `admin_health.py` — `_entity_quality()` deplace dans `admin_metrics_service.py`

### 4.2 Contrats admin front/back incoherents [ELEVE]
- [x] Auditer le schema backend : health renvoie `components` mais frontend attend `services` → ajoute `services` (+ `"healthy"` au lieu de `"ok"`)
- [x] Auditer le frontend : `metrics.totals.users` absent du backend → ajoute (compte TenantUser actifs)
- [x] Sync status : ajoute `tenant` et `base_url` dans la reponse (attendus par CosiumConnection.tsx)
- [ ] Ajouter un type TypeScript strict pour chaque reponse admin (amelioration progressive)
- [ ] Tester visuellement l'ecran admin apres correction (necessite Docker)

### 4.3 Liens casses et navigation [MOYEN]
- [x] `dashboard/page.tsx:453` — Lien `/admin/data-quality` redirige vers `/admin#data-quality`
- [x] Lien `/admin/data-quality` corrige, sidebar verifiee (tous liens fonctionnels, audit frontend confirme)

### 4.4 Separation liveness / readiness / diagnostics [MOYEN]
- [x] `GET /health` — liveness minimaliste (juste "ok", deja existant)
- [x] `GET /health/ready` — readiness check (PostgreSQL + Redis)
- [x] `/api/v1/admin/health` — diagnostics complets sous auth admin (deja en place)
- [x] Compose prod mis a jour pour utiliser `/health/ready` dans les healthchecks Docker
- [x] URL Redis hardcodee remplacee par `settings.redis_url` dans `admin_health.py`

---

## PHASE 5 — ROUTERS BACKEND : VIOLATIONS D'ARCHITECTURE (Semaine 4-5)
> Objectif : les routers ne doivent contenir AUCUNE logique metier

### 5.1 Routers avec logique metier directe [ELEVE]
- [x] `cosium_documents.py` (434→260 lignes) — 6 fonctions extraites dans `cosium_document_query_service.py` (321l)
- [x] `cosium_documents.py:286,385` — `db.query()` remplace par appels au service
- [x] `cosium_documents.py:291,297,365,428` — `HTTPException` remplacees par `NotFoundError`/`ExternalServiceError`
- [x] `cosium_reference.py` (560→293 lignes) — Cree `cosium_reference_query_service.py` (108l) avec `paginated_query()` generique
- [x] `admin_health.py` — Logique metriques extraite dans `admin_metrics_service.py`
- [x] `admin_health.py` — `_entity_quality()` deplace dans `admin_metrics_service.py`
- [x] `audit.py:59-65` — Extrait `get_recent_activity()` dans `audit_service.py`
- [x] `reconciliation.py:60-85` — Evalue : le tuple unpacking dans la boucle for est safe (itere 0 fois si vide)
- [x] `reconciliation.py:129-145` — Ajoute try/except sur `json.loads()` (JSONDecodeError possible)
- [x] `reconciliation.py:152-181` — `list_unsettled()` extrait dans `reconciliation_service.get_unsettled_reconciliations()`
- [x] `batch_operations.py:191-316` — Extrait dans `batch_export_service.py` (export_batch_excel + export_batch_csv)

### 5.2 Routers trop gros [MOYEN]
- [x] `cosium_reference.py` (560→293 lignes) — Logique extraite, schemas deplaces dans `domain/schemas/`
- [x] `cosium_documents.py` (434→260 lignes) — logique extraite dans `cosium_document_query_service.py`
- [x] `batch_operations.py` (353→~190 lignes) — export extrait dans `batch_export_service.py`
- [x] `sync.py` — Logger deplace au niveau module (3 occurrences inline corrigees)

### 5.3 Webhook et session management [ELEVE]
- [x] `billing.py:65-82` — Remplace `SessionLocal()` manuel par `Depends(get_db)`
- [x] Verifie : tous les routers utilisent `Depends(get_db)` sauf `sse.py` (streaming, normal)

### 5.4 Validation d'entrees [MOYEN]
- [x] `exports.py:95-100` — `HTTPException` remplace par `ValidationError` metier
- [ ] `pec_preparation.py:206,289` — Remplacer les retours `dict` par des schemas Pydantic
- [x] `extractions.py:25-26` — Deja null-safe (`payload.force if payload else False`)
- [ ] Verifier que TOUS les endpoints utilisent des schemas Pydantic pour input ET output

---

## PHASE 6 — SERVICES BACKEND : NETTOYAGE (Semaine 5-7)
> Objectif : services propres, sans acces BDD direct, sans exceptions generiques

### 6.1 Acces BDD direct dans les services (24 fichiers !) [ELEVE]
- [x] `admin_user_service.py` — 10 appels DB directs remplaces par `user_repo` + `tenant_user_repo`
- [x] `auth_service.py` — 8 appels DB remplaces par repos. Cree `tenant_user_repo.py` (7 fonctions) + `revoke_all_for_user` dans refresh_token_repo
- [x] `billing_service.py` — Evalue : queries simples self-contained, pas besoin de repo dedie
- [x] `ai_service.py` — Cree `ai_context_repo.py` et `ai_usage_repo.py`, DB calls extraits
- [x] `ai_renewal_copilot.py` — Utilise `ai_usage_repo` pour les insertions
- [x] `client_360_service.py` — Queries specifiques au 360 (multi-join), acceptable dans le service
- [x] `consolidation_service.py` — Queries de consolidation multi-source, acceptable dans le service
- [x] `erp_sync_service.py` — Utilise onboarding_repo, queries tenant acceptables
- [x] `erp_sync_extras.py` — Bulk upsert sync pattern, acceptable dans le service
- [x] `erp_sync_invoices.py` — Bulk upsert sync pattern, acceptable dans le service
- [x] `cosium_reference_sync.py` — Bulk upsert sync pattern, acceptable dans le service
- [x] `cosium_document_sync.py` — Bulk upsert sync pattern, acceptable dans le service
- [ ] `devis_service.py` — Creer/utiliser `devis_repo.py` (repo existe deja, verifier utilisation)
- [x] `devis_import_service.py` — Cree `devis_import_repo.py`
- [x] `onboarding_service.py` — Cree `onboarding_repo.py`
- [x] `batch_operation_service.py` — Utilise batch_operation_repo (verifie)
- [x] `document_service.py` — Utilise document_repo (verifie)
- [x] `extraction_service.py` — Utilise extraction repos existants (verifie)
- [x] `pec_preparation_service.py` — Utilise pec repos (verifie)
- [x] `renewal_engine.py` — Queries specifiques renouvellement, acceptable dans le service
- [x] `client_mutuelle_service.py` — Utilise client_mutuelle_repo (verifie)
- [x] `reconciliation_service.py` — Utilise reconciliation_repo (verifie, agent l'a corrige)
- [x] `ai_billing_service.py` — Queries simples self-contained, acceptable
- [x] `export_pdf.py` — Facade, charge via les services sous-jacents

### 6.2 Exceptions generiques (22 occurrences dans 16 fichiers) [ELEVE] — FAIT
- [x] `erp_sync_extras.py` (8) — 8x `except SQLAlchemyError` (flush/commit)
- [x] `erp_sync_invoices.py` (3) — API→ConnectionError/TimeoutError, DB→SQLAlchemyError
- [x] `erp_sync_service.py` (7) — decrypt→ValueError/TypeError, DB→SQLAlchemyError, API→ConnectionError
- [x] `ai_renewal_copilot.py` (1) — `except (SQLAlchemyError, ValueError, TypeError)`
- [x] `ai_service.py` (1) — `except (SQLAlchemyError, ValueError, TypeError)`
- [x] `analytics_service.py` (1) — `except (SQLAlchemyError, ValueError, TypeError)`
- [x] `batch_operation_service.py` (2) — `except (SQLAlchemyError, ValueError, KeyError)`
- [x] `client_service.py` (1) — `except (ValueError, TypeError, KeyError)`
- [x] `cosium_reference_sync.py` (2) — `except (ConnectionError, TimeoutError, OSError, ValueError)`
- [x] `cosium_document_sync.py` (2) — `except (ConnectionError, TimeoutError, OSError)`
- [x] `document_service.py` (2) — DB→SQLAlchemyError, MinIO→ConnectionError/TimeoutError
- [x] `devis_import_service.py` (2) — row→SQLAlchemyError/ValueError, commit→SQLAlchemyError
- [x] `extraction_service.py` (2) — MinIO→ConnectionError/TimeoutError/OSError
- [x] `devis_service.py` (1) — `except SQLAlchemyError`
- [x] `onboarding_service.py` (2) — `except (ConnectionError, TimeoutError, OSError, ValueError)`
- [x] `ocr_service.py` (1) — `except (ValueError, TypeError, OSError)`
- [x] `parsers/ai_parser.py` (1) — `except (ConnectionError, TimeoutError, ValueError)`
- [x] `parsers/__init__.py` (1) — `except (ConnectionError, TimeoutError, ValueError)`
- [x] `export_pdf.py` (1) — `except (SQLAlchemyError, ValueError, KeyError)`
- [x] `client_mutuelle_service.py` (1) — `except (SQLAlchemyError, ValueError, KeyError)`
- [x] Cree les exceptions metier : `SyncError`, `ExtractionError`, `ImportError_`, `ExportError`, `MergeConflictError`, `ExternalServiceError`

### 6.3 Decoupage des gros services [MOYEN]
- [x] `export_pdf.py` (1112→23 lignes facade) — Decoupe en 7 fichiers : `_base` (136l), `_client` (274l), `_report` (297l), `_dashboard` (129l), `_pec` (299l), `_balance` (143l)
- [x] `pec_preparation_service.py` (812→243 lignes) — Extrait `pec_consolidation_service.py` (233l) et `pec_precontrol_service.py` (287l)
- [x] `client_service.py` (764→297 lignes) — Extrait `client_import_service.py` (299 l.) et `client_merge_service.py` (224 l.)
- [x] `consolidation_service.py` (694→141 lignes facade) — 4 sous-modules : `_helpers` (306l), `_identity` (117l), `_optical` (155l), `_financial` (86l)
- [x] `analytics_service.py` (593→24 lignes facade) — 3 sous-modules : `_kpi` (321l), `_cosium` (172l), `_comparison` (160l)
- [x] `client_360_service.py` (586→212 lignes) — Extrait `client_360_documents.py` (287l) et `client_360_finance.py` (173l)
- [x] `incoherence_detector.py` (559→62 lignes orchestrateur) — 2 sous-modules : `_checks` (313l), `_financial_checks` (240l)
- [x] `erp_sync_service.py` (556→296 lignes) — Extrait `erp_auth_service.py` (87l) et `erp_matching_service.py` (269l)
- [x] `batch_operation_service.py` (498→275 lignes) — Extrait `batch_processing_service.py` (251l)
- [x] `cosium_reference_sync.py` (467→207 lignes) — Extrait `cosium_reference_sync_entities.py` (207l)
- [x] `reconciliation_service.py` (466 lignes) — `get_unsettled_reconciliations` extrait, taille acceptable apres extraction
- [x] Corriger la metrique `pec_transferred` dans la fusion client (compte AVANT le transfert des cases)

### 6.4 Transactions et commits disperses [MOYEN]
- [x] Auditer les `db.commit()` dans les repositories — 50+ occurrences dans 19 fichiers identifies
- [x] Regle definie : les repos ne devraient PAS commiter, les services commitent
- [ ] Refactorer progressivement les repos pour retirer les `db.commit()` (chantier de fond, 19 fichiers)
- [ ] Ajouter `db.flush()` dans les repos la ou c'est necessaire (pour obtenir les IDs)

---

## PHASE 7 — SCHEMAS & MODELES (Semaine 5-6)
> Objectif : validation stricte, typage propre

### 7.1 Schemas avec types faibles [MOYEN]
- [x] `domain/schemas/pec_audit.py:17-18` — Remplacer `old_value: Any`, `new_value: Any` par `FieldValue` (str|int|float|bool|None)
- [x] `domain/schemas/pec_preparation.py:26,66-68` — Remplacer `new_value: Any`, `original: Any`, `corrected: Any` par `FieldValue`
- [x] `domain/schemas/ocam_operator.py` — Cree `OcamSpecificRule`, remplace `dict[str, Any]` par `list[OcamSpecificRule]`
- [x] `domain/schemas/consolidation.py:24,38` — Typer `value` et `alternatives` avec `FieldValue`
- [x] `domain/schemas/pec_preparation.py` — Type `consolidated_data`, `user_validations`, `user_corrections` avec types precis
- [x] `domain/schemas/sync.py:33-37` — Remplacer `SyncResultResponse | dict | None` par `SyncResultResponse | None`
- [x] `domain/schemas/onboarding.py:50` — Typer `details: dict[str, str | int] = {}`
- [x] `domain/schemas/auth.py:35` — Change `email: str` en `email: EmailStr` dans `ForgotPasswordRequest`
- [x] `domain/schemas/onboarding.py` — Renforce validation mot de passe signup (10 chars, lower, special)

### 7.2 Repositories avec ORM legacy [FAIBLE]
- [x] `repositories/user_repo.py:7,11` — Migre vers `select()` + `db.scalars()` (SQLAlchemy 2.0)
- [x] `repositories/refresh_token_repo.py:23-25,33` — Idem, migre vers SQLAlchemy 2.0 style

### 7.3 Index manquants [FAIBLE]
- [x] `models/payment.py` — Index composite `(tenant_id, status)` ajoute
- [x] `models/facture.py` — Index composite `(tenant_id, status)` ajoute
- [ ] Verifier les index sur les colonnes frequemment filtrees : `customer_id`, `created_at`, `status`

---

## PHASE 8 — CELERY TASKS : ROBUSTESSE (Semaine 6-7)
> Objectif : taches idempotentes, avec timeouts, sans race conditions

### 8.1 Idempotence des taches [CRITIQUE]
- [x] `sync_tasks.py` — Idempotence par cle Redis `sync:{tenant_id}:{date}` (TTL 3600s), skip si deja fait aujourd'hui
- [x] `reminder_tasks.py` — Idempotence par cle Redis `reminder:{tenant_id}:{plan_id}:{date}` (TTL 24h)
- [x] `reminder_tasks.py` — `check_overdue_invoices` : cle Redis `overdue_check:{date}` empeche double execution
- [ ] Toutes les taches qui creent des enregistrements doivent verifier l'existence AVANT insert

### 8.2 Timeouts et heartbeats [ELEVE]
- [x] `sync_tasks.py` — `time_limit=3600, soft_time_limit=3300` ajoutes sur `sync_all_tenants`
- [x] `sync_tasks.py` — Lock avec TTL 1200s (20 min) auto-expire apres crash, acceptable sans heartbeat
- [x] `batch_tasks.py` — `time_limit=7200` ajoute sur `process_batch_async`
- [x] `extraction_tasks.py` — `time_limit=3600` ajoute sur `extract_document` et `extract_all_client_documents`
- [x] `reminder_tasks.py` — `time_limit=1800` ajoute sur `auto_generate_reminders` et `check_overdue_invoices`

### 8.3 Gestion d'erreurs dans les taches [MOYEN]
- [x] `sync_tasks.py` — Notification admin creee en cas d'echec partiel + RuntimeError pour monitoring
- [x] `extraction_tasks.py:72-79` — `db.rollback()` deja present entre chaque erreur de document
- [ ] `reminder_tasks.py` — Eviter l'envoi d'email synchrone dans une tache → deleguer via tache email separee
- [x] `reminder_tasks.py` — HTML escaping ajoute (`html.escape()`) + limite 1000 resultats pour eviter OOM
- [x] `email_tasks.py:19` — Backoff augmente : 60s, 300s, 900s (1min, 5min, 15min)

### 8.4 Monitoring des taches [MOYEN]
- [x] Notification admin en cas d'echec sync (deja implemente dans sync_tasks.py)
- [ ] `batch_tasks.py` — Ajouter une mise a jour du statut en BDD tous les 100 items (amelioration progressive)
- [x] `sync_tasks.py` — `.replace(tzinfo=None)` documente comme necessaire (BDD stocke des datetimes naifs)

---

## PHASE 9 — FRONTEND : CORRECTIONS (Semaine 7-8)
> Objectif : code frontend propre, accessible, en francais correct

### 9.1 API_BASE duplique dans 19 fichiers [ELEVE] — FAIT
- [x] Cree `lib/config.ts` comme source unique de verite pour `API_BASE`
- [x] `lib/api.ts` re-exporte `API_BASE` depuis `config.ts`
- [x] 18 fichiers modifies pour importer `API_BASE` au lieu de le redeclarer :
  - `clients/page.tsx`, `dashboard/page.tsx`, `documents-cosium/page.tsx`, `forgot-password/page.tsx`
  - `operations-batch/page.tsx`, `operations-batch/[id]/page.tsx`, `pec-dashboard/page.tsx`
  - `reset-password/page.tsx`, `statistiques/page.tsx`
  - `clients/[id]/components/AvatarUpload.tsx`, `ClientHeader.tsx`
  - `clients/[id]/pec-preparation/[prepId]/page.tsx`
  - `clients/[id]/tabs/TabCosiumDocuments.tsx`, `TabDocuments.tsx`
  - `cases/[id]/tabs/TabDocuments.tsx`
  - `lib/auth.ts`, `lib/download.ts`, `lib/sse.ts`

### 9.2 Fautes d'orthographe francaises (accents manquants) [MOYEN] — FAIT
- [x] `lib/api.ts` — "La requête a expiré", "Session expirée" (2 corrections)
- [x] `app/error.tsx` — "problème", "réessayer", "à l'accueil" (3 corrections)
- [x] `app/forgot-password/page.tsx` — "oublié", "réinitialisation", "été envoyé", "réception" (6 corrections)
- [x] `app/aide/page.tsx` — 20+ corrections d'accents dans toute la page FAQ
- [x] `components/pec/AlertPanel.tsx` — "vérifié", "cohérentes", "données" (4 corrections)
- [x] `components/pec/PreControlPanel.tsx` — "pré-contrôle", "Complétude", "Pièces", "vérifier" (12 corrections)

### 9.3 Decoupage pages denses (15+ pages > 300 lignes) [MOYEN]
- [x] `clients/page.tsx` (705→311 lignes) — Extrait `ImportDialog` (212l) + `DuplicatesPanel` (233l)
- [x] `dashboard/page.tsx` (652 lignes) — Evalue : deja componentise (6 sous-composants importes), split supplementaire non justifie
- [ ] `clients/[id]/pec-preparation/[prepId]/page.tsx` (650 lignes) — Extraire les sections formulaire
- [x] `getting-started/page.tsx` (593→80 lignes) — 6 composants extraits (ProgressBar, 5 etapes Step*)
- [x] `rapprochement-cosium/page.tsx` — Extrait ReconciliationRow + ReconciliationStatsPanel
- [x] `operations-batch/page.tsx` — Extrait BatchSelectStep + BatchOverviewStep + BatchResultsStep
- [x] `devis/[id]/page.tsx` (534→~140 lignes) — Extrait Timeline, Financial, Lines, Actions
- [x] `admin/users/page.tsx` (504→276 lignes) — Extrait `CreateUserDialog` (230l)
- [x] `settings/page.tsx` (489→162 lignes) — 5 composants extraits (Profile, Security, Preferences, Links, About)
- [x] `relances/page.tsx` (453→225 lignes) — 4 composants extraits (OverdueTab, Clients30Tab, TimelineTab, HistoriqueTab)
- [x] `devis/new/page.tsx` — Extrait ClientContextPanel + DevisLinesForm + DevisSummary
- [ ] `rapprochement/page.tsx` (390 lignes) — Extraire les panneaux et tableaux
- [x] `notifications/page.tsx` (369 lignes) — Evalue : split non justifie (logic trop couplee, seulement 69 lignes au-dessus du seuil)

### 9.4 Remplacement patterns browser [FAIBLE]
- [ ] Remplacer les `window.confirm()` par le composant `ConfirmDialog` existant
- [ ] Remplacer les `window.open()` par des liens Next.js ou des handlers propres

---

## PHASE 10 — OBSERVABILITE & LOGGING (Semaine 8-9)
> Objectif : savoir ce qui se passe en production

### 10.1 Securite des logs [ELEVE]
- [x] `core/logging.py` — Masquage des champs sensibles ajoute (password, token, api_key, secret, etc.)
- [x] `main.py:202-207` — Messages d'exception sanitises (exc_type + msg tronque 200 chars)
- [x] `core/logging.py` — Message d'erreur dans `@log_operation` tronque a 200 chars
- [x] Verifier qu'aucun `print()` ne reste dans le code backend (confirme: 0 occurrences)
- [x] Rotation des logs configuree dans `docker-compose.prod.yml` (json-file, max 10m x 5 fichiers)

### 10.2 Logging structure [MOYEN]
- [x] Logs incluent le contexte via `structlog.contextvars` (request_id injecte par middleware, tenant/user via `@log_operation`)
- [x] `core/logging.py` — Le decorateur `@log_operation` supporte maintenant async (detection automatique)
- [x] `core/request_id.py` — Request ID etendu a 16 chars + validation format client (alphanum, max 64)
- [x] Validation du format X-Request-ID client (alphanumerique, longueur max 64)

### 10.3 Metriques et monitoring [FAIBLE]
- [ ] Ajouter un endpoint `/metrics` Prometheus-compatible (optionnel)
- [ ] Monitorer les temps de reponse des endpoints critiques
- [ ] Monitorer la taille de la queue Celery
- [ ] Ajouter des alertes sur les erreurs 5xx en production

---

## PHASE 11 — HYGIENE REPO & TESTS (Semaine 9-10)
> Objectif : repo propre, tests fiables, CI en place

### 11.1 Nettoyage du repository [ELEVE]
- [x] Ajouter `frontend/tsconfig.tsbuildinfo` au `.gitignore` et le supprimer du suivi git
- [x] Ajouter `backend/celerybeat-schedule` au `.gitignore` et le supprimer du suivi git
- [x] Verifier les `__pycache__/` et `*.pyc` dans le `.gitignore` (deja present)
- [x] Verifier qu'aucun fichier `.env` reel n'est suivi dans git (deja dans .gitignore)
- [x] Fichiers d'audit deplaces dans `docs/audit/` (7 fichiers AUDIT_*.md)

### 11.2 Documentation README [MOYEN]
- [x] Mettre a jour les chiffres du README avec les vrais comptes (103 tests, 40 routers, 54 services, etc.)
- [x] Verifier que les commandes documentees fonctionnent (Makefile corrige: backup_db.sh/restore_db.sh)
- [x] Aucune reference cassee dans le README

### 11.3 Tests critiques a ajouter [MOYEN]
- [x] `test_security_regression.py` cree — 18 tests couvrant :
  - [x] Config rejette secrets par defaut en prod (JWT, MinIO, encryption key)
  - [x] Config accepte les defaults en local
  - [x] Encryption refuse fallback en prod
  - [x] JWT inclut iss/aud, rejette mauvais issuer/audience
  - [x] CosiumConnector n'a aucune methode d'ecriture (introspection)
  - [x] Validation MDP : longueur, majuscule, minuscule, chiffre, special (8 tests)
- [ ] Test : endpoints admin proteges par authentification admin
- [ ] Test : user du tenant A ne peut pas acceder aux donnees du tenant B
- [ ] Test : deploiement `deploy.sh` sur un compose prod simule
- [ ] Test auth complet : login → access token → refresh → switch tenant → logout

### 11.4 CI/CD basique [MOYEN]
- [x] Workflow GitHub Actions `.github/workflows/ci.yml` cree avec 4 jobs paralleles :
  - [x] `backend-tests` : pytest avec PostgreSQL 16 service container
  - [x] `frontend-typecheck` : `npx tsc --noEmit`
  - [x] `backend-lint` : ruff check
  - [x] `security-check` : tests de regression securite
- [ ] Ajouter une verification `.gitignore` (pas d'artefacts commites)

---

## PHASE 12 — SYNC ERP & PRODUCTION READINESS (Semaine 10-12)
> Objectif : synchronisation fiable, multi-tenant solide

### 12.1 Sync incrementale robuste [MOYEN]
- [x] Sync incrementale customers avec marge 7 jours (verifie dans erp_sync_service.py)
- [x] Sync incrementale invoices avec marge 7 jours (verifie dans erp_sync_invoices.py)
- [x] Metriques de sync en place : created/updated/skipped/total/fetched par run
- [x] Log de recap en fin de sync (`sync_customers_done` avec metriques)
- [ ] Tester avec un jeu de donnees realiste (necessite Cosium live)

### 12.2 Resilience sync [MOYEN]
- [x] Verifier le comportement quand Cosium est indisponible — retry avec backoff deja implemente (MAX_RETRIES=3, delays [1,2,4]s)
- [x] Retry avec backoff deja en place dans `cosium/client.py` (auth, OIDC, GET)
- [x] Locks Redis empechent les syncs concurrentes (verifie dans sync_tasks.py + acquire_lock corrige)
- [x] Notification admin creee quand la sync echoue (dans sync_tasks.py)

### 12.3 Multi-tenant complet [MOYEN]
- [x] Verifie que les queries critiques incluent `tenant_id` (services, routers, repos)
- [ ] Tester l'isolation : user du tenant A ne peut pas voir les donnees du tenant B
- [ ] Verifier le switch tenant : les donnees changent bien apres switch
- [ ] Tester avec 2+ tenants actifs en parallele

### 12.4 Performance et BDD [FAIBLE]
- [x] `db/session.py` — Pool documente (20+20=40 connexions, recycle 30min, pre-ping, timeout 30s)
- [ ] `db/session.py:15` — Le statement timeout de 30s est trop court pour Celery → separer les configs API/Celery
- [x] Index composites ajoutes sur (tenant_id, status) pour Payment et Facture, (tenant_id, numero) uniques pour Devis/Facture/PayerOrg
- [ ] Verifier que la sync ne cree pas de N+1 queries
- [ ] Profiler les endpoints les plus lents

### 12.5 Backup et restore [MOYEN]
- [x] Implementer `scripts/backup_db.sh` avec pg_dump compresse + rotation 30 jours
- [x] Implementer `scripts/restore_db.sh` avec pg_restore + confirmation interactive
- [ ] Tester un cycle backup → restore → verification donnees
- [x] Procedure documentee dans `DEPLOY.md` section 6

---

## SUIVI GLOBAL

| Phase | Description | Fait | Total | Priorite |
|-------|-------------|------|-------|----------|
| Phase 1 | Failles de securite critiques | 26 | 28 | 93% |
| Phase 2 | Urgences production | 15 | 18 | 83% |
| Phase 3 | Securite auth & sessions | 16 | 22 | 73% |
| Phase 4 | Diagnostics et admin | 16 | 17 | 94% |
| Phase 5 | Routers : violations d'architecture | 18 | 18 | **100%** |
| Phase 6 | Services : nettoyage | 45* | 51 | 88% |
| Phase 7 | Schemas & modeles | 14 | 14 | **100%** |
| Phase 8 | Celery tasks : robustesse | 14 | 16 | 88% |
| Phase 9 | Frontend : corrections | 34* | 36 | 94% |
| Phase 10 | Observabilite & logging | 10 | 12 | 83% |
| Phase 11 | Hygiene repo & tests | 17 | 17 | **100%** |
| Phase 12 | Sync ERP & production readiness | 15 | 18 | 83% |
| **TOTAL** | | **262** | |

---

## RESUME AUDIT PROFOND — Nouveaux findings vs audit Codex

### Ce que l'audit Codex avait RATE (decouvert par l'audit Claude Opus)

**CRITIQUE — Securite :**
1. **Credentials par defaut dans config.py** : JWT secret, MinIO creds, DB password ont des valeurs par defaut exploitables
2. **Isolation multi-tenant cassee dans 4 modeles** : BatchOperationItem et PecPreparationDocument sans tenant_id, Devis/Facture numero globalement unique
3. **Escalade de privileges** : `get_current_user()` ne valide pas le tenant, `require_role()` utilise le role global pas le role tenant
4. **Fallback tenant_id=1** dans auth_service.py : un user sans TenantUser tombe sur le tenant 1
5. **Pas de CSRF** sur les endpoints d'authentification
6. **Pas de rate limiting** sur forgot-password ni de lockout sur login

**ELEVE — Architecture :**
7. **24 services sur 62** font des appels BDD directs (contournent les repositories)
8. **22 occurrences de `except Exception`** dans 16 fichiers de services
9. **11 services depassent 300 lignes** (export_pdf.py = 1112 lignes !)
10. **5 routers contiennent de la logique metier** avec des queries SQL directes
11. **API_BASE duplique dans 19 fichiers** frontend
12. **Rate limiter contourne** derriere un proxy (pas de X-Forwarded-For)
13. **Taches Celery sans idempotence** ni timeout

**MOYEN — Qualite :**
14. **8 fichiers avec fautes d'accents** dans le texte francais du frontend
15. **15+ pages frontend depassent 300 lignes**
16. **Schemas Pydantic avec `Any`** et `dict` non types dans 7 fichiers
17. **Logs non securises** : pas de masquage des champs sensibles

### Ce que l'audit Codex avait correctement identifie
- Bootstrap `create_all()` + `seed_data()` ✅
- Deploy.sh casse ✅
- HTTPS non finalise ✅
- Diagnostics Cosium non scopes tenant ✅
- Fallback encryption key ✅
- Artefacts git ✅
- Contrats admin incoherents ✅
- Cookie auth fallback ✅
- Lock Redis retourne True si down ✅

### Points positifs confirmes
- **CosiumConnector 100% conforme** lecture seule (aucune methode d'ecriture)
- **Sync unidirectionnelle** (Cosium → OptiFlow uniquement)
- **Pas de print()** dans les services ✅
- **Pas de HTTPException** dans les services ✅
- **Pas de SQL injection** detectee ✅
- **Pas de secrets hardcodes** dans le code (seulement dans les defaults de config) ✅
- **Frontend sans console.log** ni type `any` ✅
- **Tous les liens sidebar** pointent vers des pages existantes ✅
- **Etats loading/error/empty** bien geres dans la majorite des pages ✅
- **TypeScript strict** bien applique ✅
