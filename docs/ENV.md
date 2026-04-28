# Variables d'environnement OptiFlow

> Source : `apps/api/app/core/config.py` — toutes les vars y sont définies via Pydantic Settings.

## Convention

- Format `.env` à la racine du projet
- Préfixe `_DEV_*` = valeurs par défaut **dev seulement**, refusées en `production`/`staging` (voir `_validate_production_secrets`)
- Variables marquées **OBLIGATOIRE** doivent être fournies en prod/staging

## Application

| Variable | Type | Défaut | Description |
|----------|------|--------|-------------|
| `APP_ENV` | str | `local` | `local`, `dev`, `staging`, `production`, `test` |
| `SEED_ON_STARTUP` | bool | `true` | Seed auto en dev (passer à `false` en prod) |
| `CELERY_WORKER` | bool | `false` | `true` si exécuté dans un worker (timeout DB plus long) |

## Base de données

| Variable | Défaut | Description |
|----------|--------|-------------|
| `DATABASE_URL` | `postgresql+psycopg://optiflow:optiflow@postgres:5432/optiflow` | URL SQLAlchemy. **OBLIGATOIRE** en prod, doit utiliser des creds sécurisés |
| `POSTGRES_DB` | `optiflow` | Utilisé par docker-compose |
| `POSTGRES_USER` | `optiflow` | Utilisé par docker-compose |
| `POSTGRES_PASSWORD` | `optiflow` | Utilisé par docker-compose |

## Authentification & sécurité

| Variable | Défaut | Description |
|----------|--------|-------------|
| `JWT_SECRET` | `dev-only-change-me-super-secret` | **OBLIGATOIRE** en prod. Min 32 chars HS256. Générer : `python -c 'import secrets; print(secrets.token_urlsafe(64))'` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Durée access token JWT |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Durée refresh token |
| `ENCRYPTION_KEY` | `""` | **OBLIGATOIRE** en prod (Fernet). Générer : `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'` |

## CORS

| Variable | Défaut | Description |
|----------|--------|-------------|
| `CORS_ORIGINS` | `http://localhost:3000` | Liste séparée par virgules. **JAMAIS `*`** en prod |

## Rate limiter (proxy)

| Variable | Défaut | Description |
|----------|--------|-------------|
| `TRUSTED_PROXIES` | `""` | Liste CSV d'IPs autorisées à fournir un `X-Forwarded-For` fiable. **Obligatoire en prod derrière nginx** (typiquement `127.0.0.1`). Sans elle, le rate limiter bucketise tout le trafic sur l'IP du proxy → un seul utilisateur peut bloquer tout le monde. L'API logue un warning au boot si `APP_ENV=production/staging` et la valeur est vide. |

## Stockage S3 / MinIO

| Variable | Défaut | Description |
|----------|--------|-------------|
| `S3_ENDPOINT` | `http://minio:9000` | URL S3-compatible |
| `S3_ACCESS_KEY` | `minioadmin` | **OBLIGATOIRE** en prod, !=`minioadmin` |
| `S3_SECRET_KEY` | `minioadmin` | **OBLIGATOIRE** en prod, !=`minioadmin` |
| `S3_BUCKET` | `optiflow-docs` | Bucket pour les documents |

## Redis & Celery

| Variable | Défaut | Description |
|----------|--------|-------------|
| `REDIS_URL` | `redis://redis:6379/0` | Broker + backend Celery |

## Email (Mailhog en dev)

| Variable | Défaut | Description |
|----------|--------|-------------|
| `MAILHOG_SMTP_HOST` | `mailhog` | SMTP en dev. Remplacer par vrai SMTP en prod (Sendgrid, SES, etc.) |
| `MAILHOG_SMTP_PORT` | `1025` | Port SMTP |

## IA (Anthropic)

| Variable | Défaut | Description |
|----------|--------|-------------|
| `ANTHROPIC_API_KEY` | `""` | API key Claude. Requis pour features IA (OCR, copilote) |
| `AI_MODEL` | `claude-haiku-4-5-20251001` | Modèle utilisé. Voir CLAUDE.md pour les IDs |

## Stripe (facturation SaaS OptiFlow)

| Variable | Défaut | Description |
|----------|--------|-------------|
| `STRIPE_SECRET_KEY` | `""` | sk_live_* en prod, sk_test_* en dev |
| `STRIPE_WEBHOOK_SECRET` | `""` | whsec_* (vérification webhooks) |
| `STRIPE_PRICE_SOLO` | `""` | Stripe price ID plan Solo |
| `STRIPE_PRICE_RESEAU` | `""` | Stripe price ID plan Réseau |
| `STRIPE_PRICE_IA_PRO` | `""` | Stripe price ID add-on IA Pro |

## Cosium API (LECTURE SEULE — voir [COSIUM_AUTH.md](COSIUM_AUTH.md))

| Variable | Défaut | Description |
|----------|--------|-------------|
| `COSIUM_BASE_URL` | `https://c1.cosium.biz` | URL base API Cosium |
| `COSIUM_TENANT` | `""` | Slug du tenant Cosium |
| `COSIUM_LOGIN` | `""` | Login Basic Auth |
| `COSIUM_PASSWORD` | `""` | Password Basic Auth |
| `COSIUM_OIDC_TOKEN_URL` | `""` | Endpoint OIDC token (mode SSO) |
| `COSIUM_OIDC_CLIENT_ID` | `""` | Client ID OIDC |
| `COSIUM_ACCESS_TOKEN` | `""` | Cookie access_token (mode interactif, dev only) |
| `COSIUM_DEVICE_CREDENTIAL` | `""` | Cookie device-credential (idem) |

## Upload

| Variable | Défaut | Description |
|----------|--------|-------------|
| `MAX_UPLOAD_SIZE_MB` | `20` | Taille max upload. Doit rester ≤ `client_max_body_size` nginx (25M actuel) |

## Monitoring

| Variable | Défaut | Description |
|----------|--------|-------------|
| `SENTRY_DSN` | `""` | Sentry DSN backend (vide = désactivé) |
| `NEXT_PUBLIC_SENTRY_DSN` | `""` | Sentry DSN frontend (build-time) |

## Frontend (Next.js, build-time)

| Variable | Défaut | Description |
|----------|--------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api/v1` | Base URL appelée par le frontend |

## Backups (scripts maintenance)

| Variable | Défaut | Description |
|----------|--------|-------------|
| `BACKUP_RETENTION_DAYS` | `90` | Durée rétention backups |
| `BACKUP_MIN_FREE_MB` | `500` | Espace libre minimum requis avant backup |
| `BACKUP_ALERT_WEBHOOK` | `""` | Webhook Slack/Discord pour alertes monitor backup |
| `MAX_AGE_HOURS` | `25` | Seuil alerte âge dernier backup |

## Déploiement

| Variable | Défaut | Description |
|----------|--------|-------------|
| `DEPLOY_BRANCH` | `main` | Branche source pour `scripts/deploy.sh` |

## Validation production

`Settings._validate_production_secrets` (config.py:74) refuse au démarrage si `APP_ENV in (production, staging)` et :
- `JWT_SECRET` reste à la valeur dev ou contient "change-me"
- `S3_ACCESS_KEY` ou `S3_SECRET_KEY` == `minioadmin`
- `ENCRYPTION_KEY` vide
- `DATABASE_URL` reste la valeur dev
- `CORS_ORIGINS` contient `*`

L'API plante au boot avec un message explicite si l'une de ces conditions est violée.

## Exemple `.env.prod`

```bash
APP_ENV=production
SEED_ON_STARTUP=false

# DB
DATABASE_URL=postgresql+psycopg://optiflow:STRONG_PWD@postgres:5432/optiflow
POSTGRES_PASSWORD=STRONG_PWD

# Auth
JWT_SECRET=<output de python -c 'import secrets; print(secrets.token_urlsafe(64))'>
ENCRYPTION_KEY=<output de Fernet.generate_key().decode()>

# S3
S3_ACCESS_KEY=optiflow-prod
S3_SECRET_KEY=<password fort>

# CORS strict
CORS_ORIGINS=https://app.optiflow.example.com

# Email
MAILHOG_SMTP_HOST=smtp.sendgrid.net
MAILHOG_SMTP_PORT=587

# Cosium
COSIUM_TENANT=mon-magasin
COSIUM_LOGIN=optiflow-readonly
COSIUM_PASSWORD=<mot de passe>

# Frontend (build-time)
NEXT_PUBLIC_API_BASE_URL=https://app.optiflow.example.com/api/v1

# Monitoring
SENTRY_DSN=https://...@sentry.io/...
```
