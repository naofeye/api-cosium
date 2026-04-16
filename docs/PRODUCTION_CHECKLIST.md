# Checklist de mise en production

Toutes les étapes à compléter avant d'exposer OptiFlow AI à un usage production réel.

## 1. Secrets & credentials

### 1.1 Générer les secrets (uniques par environnement)

```bash
# JWT (min 32 caractères, jamais réutilisé)
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Fernet (clé de chiffrement PII)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# PostgreSQL admin password
python -c "import secrets; print(secrets.token_urlsafe(24))"

# MinIO access + secret
python -c "import secrets; print(secrets.token_urlsafe(20))"
python -c "import secrets; print(secrets.token_urlsafe(40))"

# Grafana admin
python -c "import secrets; print(secrets.token_urlsafe(16))"
```

### 1.2 Rotation Cosium

- [ ] **Révoquer** le compte applicatif actuel (`AFAOUSSI`) via admin Cosium
- [ ] **Créer** un compte dédié `OPTIFLOW_SERVICE` avec droits lecture seule
- [ ] **Stocker** le mot de passe dans `.env` prod chiffré (Ansible Vault, Bitwarden, AWS Secrets Manager)
- [ ] **Purger** l'historique Git : `git filter-branch` ou BFG Repo Cleaner si des secrets ont été commit

### 1.3 Variables d'environnement prod

Dans `.env.production` :

```env
APP_ENV=production
DATABASE_URL=postgresql+psycopg://optiflow:<STRONG_PASSWORD>@postgres:5432/optiflow
JWT_SECRET=<48+ char random>
ENCRYPTION_KEY=<Fernet generated key>
POSTGRES_PASSWORD=<strong>
S3_ACCESS_KEY=<random>
S3_SECRET_KEY=<random 40 char>
GF_SECURITY_ADMIN_PASSWORD=<strong>
COSIUM_LOGIN=OPTIFLOW_SERVICE
COSIUM_PASSWORD=<rotated>
SENTRY_DSN=https://...@sentry.io/...
CORS_ORIGINS=https://optiflow.votre-domaine.com
```

## 2. Infrastructure TLS

### 2.1 Nginx HTTPS

- [ ] Décommenter le bloc SSL dans `config/nginx/nginx.conf:122-198`
- [ ] Configurer **server_name** avec le vrai domaine (pas `_` catch-all `nginx.conf:49`)
- [ ] Installer **Let's Encrypt** via Certbot :
  ```bash
  sudo certbot certonly --nginx -d optiflow.votre-domaine.com
  ```
- [ ] Redirect HTTP → HTTPS activé
- [ ] Headers sécurité activés (HSTS, X-Frame-Options, CSP déjà configurés côté Next)

### 2.2 DNS & domaine

- [ ] A record pointe vers l'IP VPS
- [ ] Test HTTPS avec [ssllabs.com](https://www.ssllabs.com/ssltest/) → note minimum A

## 3. Base de données

- [ ] **Backup initial** : `./scripts/backup.sh`
- [ ] **Cron backup quotidien** : `0 2 * * * cd /srv/optiflow && ./scripts/backup.sh`
- [ ] **Off-site backup** : configurer `OFFSITE_ENDPOINT/ACCESS/SECRET/BUCKET` + cron `./scripts/backup_offsite.sh`
- [ ] **Test restore** : `./scripts/test_backup_restore.sh` passe sans erreur
- [ ] **Migrations appliquées** : `docker compose exec api alembic upgrade head`
- [ ] **Indexes critiques** présents (cf `docs/DATABASE_INDEXES.md`)

## 4. Sécurité app

- [ ] `APP_ENV=production` dans `.env` (déclenche validation stricte config)
- [ ] `JWT_SECRET` ≥ 32 caractères (vérifié par model_validator)
- [ ] `CORS_ORIGINS` = domaine(s) réel(s), **pas de `*`**
- [ ] `cookie samesite="strict"` (fait)
- [ ] Rate limiting actif (`APP_ENV != "test"`)
- [ ] `/api/v1/admin/health` détaillé sous auth admin (fait)
- [ ] Sentry DSN configuré (capture erreurs)
- [ ] **MFA/TOTP activé** pour les comptes admin (recommandé)

## 5. Observabilité

- [ ] Prometheus scrape `/api/v1/metrics` (bind 127.0.0.1 + nginx)
- [ ] Grafana admin password changé (pas `admin/admin`)
- [ ] Sentry reçoit les erreurs (test avec `/api/v1/admin/sentry-test`)
- [ ] Logs JSON structurés accessibles (`docker compose logs api | jq`)
- [ ] `/health/ready` retourne `ok` pour DB + Redis
- [ ] Celery beat heartbeat < 300s (dashboard)
- [ ] Retention logs active (quotidien 3:45)

## 6. Frontend

- [ ] `npm run build` sans warning
- [ ] `next.config.ts` : `ignoreDuringBuilds: false` (ESLint bloquant)
- [ ] Icônes PWA 192/512 + favicon présents
- [ ] CSP nonces actifs (middleware.ts)
- [ ] Service worker enregistré en prod
- [ ] Bundle analyzer audit : pas de module > 500 KB

## 7. Tests E2E

- [ ] Login admin + MFA
- [ ] Création client → dossier → devis → facture → paiement
- [ ] Sync Cosium clients + factures (read-only)
- [ ] PEC création → envoi → tracking
- [ ] Dashboard KPIs affichés
- [ ] Logout propre

## 8. Performance

- [ ] Load test 50 users concurrents < 3s P95 (`scripts/load_test.py`)
- [ ] Lighthouse score ≥ 90 (Performance + Accessibility + Best Practices + SEO + PWA)
- [ ] DB queries slow log (> 100ms) examiné

## 9. Conformité RGPD

- [ ] Droit à l'oubli fonctionne (`/clients/{id}` DELETE soft-delete + anonymisation)
- [ ] Consentements marketing trackés (`marketing_consents` table)
- [ ] Export données utilisateur disponible (endpoint à implémenter si réclamé)
- [ ] Politique de confidentialité publiée
- [ ] Mention CNIL / DPO si applicable

## 10. Plan de bascule

1. **Fenêtre de maintenance** annoncée aux clients (email J-7)
2. **Snapshot** VPS avant bascule
3. **Déploiement** : `./scripts/deploy.sh`
4. **Smoke tests** checklist ci-dessus
5. **Monitoring actif** 24h post-déploiement (Sentry alertes)
6. **Rollback** préparé : `./scripts/rollback.sh`

## 11. Gouvernance continue

- [ ] Runbook incidents (`docs/RUNBOOK.md`) à jour
- [ ] Rotation credentials : calendrier (tous les 90 jours)
- [ ] Review sécurité trimestrielle
- [ ] Dependabot PRs review hebdomadaire
- [ ] Audit Sentry erreurs hebdomadaire

## Ce qui reste en "DIFFERE-PROD" dans le TODO

Ces items sont **bloquants pour la prod** mais sans impact en env de test :

| Item | Localisation | Action |
|---|---|---|
| TLS HTTPS | `config/nginx/nginx.conf:122` | Décommenter + Certbot |
| `server_name` catch-all | `config/nginx/nginx.conf:49` | Mettre le domaine réel |
| `POSTGRES_PASSWORD` default | `docker-compose.yml` | `optiflow` → strong |
| Grafana `admin/admin` | `docker-compose.monitoring.yml:21` | `GF_SECURITY_ADMIN_PASSWORD` |
| Creds Cosium `.env` | repo | Rotation + filter-branch |
| Rate limit `app_env=local` | `core/rate_limiter.py` | Vérifier que `APP_ENV=production` en prod |

## Références

- [CLAUDE.md](../CLAUDE.md) — Règles projet
- [RBAC.md](./RBAC.md) — Permissions
- [RUNBOOK.md](./RUNBOOK.md) — Ops
- [VPS_DEPLOYMENT.md](./VPS_DEPLOYMENT.md) — Déploiement VPS
- [TODO_MASTER_AUDIT.md](../TODO_MASTER_AUDIT.md) — Suivi audit
