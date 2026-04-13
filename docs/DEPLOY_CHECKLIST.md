# Checklist deploiement production OptiFlow

> A executer dans l'ordre. Ne jamais sauter une etape sans raison documentee.

## Pre-requis (a faire UNE FOIS)

- [ ] VM/serveur provisionne (min 4 vCPU, 8 Go RAM, 100 Go SSD)
- [ ] Docker + Docker Compose v2 installes (`docker --version` >= 24)
- [ ] Domaine DNS pointe vers l'IP du serveur (record A)
- [ ] Email valide pour notifications Let's Encrypt
- [ ] Acces SSH avec cles publiques (jamais password)
- [ ] Firewall : ouvrir 80/443 uniquement, fermer 5432/6379/9000-9001/8000/3000
- [ ] Compte SMTP configure (Sendgrid/SES/OVH) — Mailhog interdit en prod
- [ ] Compte Cosium dedie OptiFlow (creds `tenant_cosium_credentials`)
- [ ] Repository acces deploy key ou GitHub Actions

## Pre-deployment (a faire CHAQUE deploiement)

- [ ] `.env` sur le serveur conforme [docs/ENV.md](ENV.md)
  - [ ] `APP_ENV=production`
  - [ ] `JWT_SECRET` >= 64 chars (genere par `secrets.token_urlsafe(64)`)
  - [ ] `ENCRYPTION_KEY` (Fernet) genere
  - [ ] `S3_ACCESS_KEY` / `S3_SECRET_KEY` != `minioadmin`
  - [ ] `DATABASE_URL` avec password fort
  - [ ] `CORS_ORIGINS` strict (pas de `*`)
  - [ ] `SEED_ON_STARTUP=false`
  - [ ] `SENTRY_DSN` configure
- [ ] Backup BDD recent (`./scripts/backup_db.sh`)
- [ ] CI verte sur le commit a deployer
- [ ] Pas de migration breaking en cours (verifier `alembic history`)
- [ ] Annonce equipe (Slack/email) si downtime > 30s prevu

## Deployment

- [ ] SSH au serveur, `cd /opt/optiflow`
- [ ] `./scripts/deploy.sh` (utilise docker-compose.yml + docker-compose.prod.yml)
  - Backup automatique pre-deploy
  - `git fetch && reset --hard origin/main`
  - Build + restart services
  - `alembic upgrade head`
  - Health check final via nginx
- [ ] Verifier `curl https://app.optiflow.example.com/api/v1/admin/health`
  - Tous services `ok` (postgres, redis, minio, cosium)
- [ ] Verifier UI : login admin, navigation dashboard

## Post-deployment

- [ ] Verifier logs API : `make logs FILTER=api` — pas d'erreur
- [ ] Verifier logs Celery : `make logs FILTER=worker` — workers ready
- [ ] Verifier Sentry : pas de pic d'erreurs
- [ ] Verifier metriques : taux 5xx < 1%, latence p95 < 500ms
- [ ] Test sync Cosium manuel sur 1 tenant
- [ ] Smoke test : creer un client + un devis + valider

## Rollback (si probleme)

- [ ] `git log --oneline -5` pour identifier le commit precedent
- [ ] `git reset --hard <commit-stable>`
- [ ] `./scripts/deploy.sh`
- [ ] Si BDD migrate echoue : `./scripts/restore_db.sh runtime/backups/pre-restore_*.dump`
- [ ] Annoncer le rollback equipe + Sentry

## TLS / Let's Encrypt (initial setup)

```bash
# 1. Demander un certificat staging d'abord (eviter rate limit prod)
docker compose run --rm certbot certonly --webroot -w /var/www/certbot \
  --staging -d app.optiflow.example.com

# 2. Verifier que ca marche
curl -kI https://app.optiflow.example.com

# 3. Demander le vrai cert
docker compose run --rm certbot certonly --webroot -w /var/www/certbot \
  -d app.optiflow.example.com

# 4. Decommenter le bloc HTTPS dans config/nginx/nginx.conf
# 5. Reload nginx
docker compose exec nginx nginx -s reload

# 6. Mettre en place renewal cron (90 jours)
0 3 * * * cd /opt/optiflow && docker compose run --rm certbot renew --quiet && docker compose exec nginx nginx -s reload
```

## Monitoring quotidien

- [ ] Sentry : pas de spike d'erreurs depuis 24h
- [ ] Backup auto : `./scripts/backup_monitor.sh` exit 0 (cron horaire)
- [ ] Disque /var/lib/docker : > 20 Go libres
- [ ] Healthcheck endpoint : `/api/v1/admin/health` → status `healthy`
- [ ] Queue Celery : pas de tasks > 5 min en attente
