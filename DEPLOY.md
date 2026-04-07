# OptiFlow AI -- Runbook de deploiement production

## 1. Prerequis

- **Serveur** : Ubuntu 22.04+ (ou Debian 12+), 4 Go RAM minimum, 40 Go disque
- **Docker** : Docker Engine 24+ et Docker Compose v2
- **Domaine** : un nom de domaine pointe vers l'IP du serveur (A record)
- **Ports ouverts** : 80 (HTTP), 443 (HTTPS)
- **Git** : acces au repo (clone ou pull)

```bash
# Verifier les prerequis
docker --version && docker compose version && git --version
```

## 2. Configuration -- Variables d'environnement

Copier `.env.example` vers `.env` et configurer toutes les valeurs.

```bash
cp .env.example .env
chmod 600 .env
```

### Variables OBLIGATOIRES en production

| Variable | Description | Comment generer |
|----------|-------------|-----------------|
| `APP_ENV` | Mettre `production` | `production` |
| `JWT_SECRET` | Secret JWT (64+ caracteres) | `openssl rand -base64 64` |
| `ENCRYPTION_KEY` | Cle Fernet pour chiffrement Cosium | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `DATABASE_URL` | URL PostgreSQL avec mot de passe fort | `postgresql+psycopg://optiflow:<MOT_DE_PASSE>@postgres:5432/optiflow` |
| `POSTGRES_PASSWORD` | Mot de passe PostgreSQL | `openssl rand -base64 32` |
| `S3_ACCESS_KEY` | Identifiant MinIO (pas `minioadmin`) | `openssl rand -hex 16` |
| `S3_SECRET_KEY` | Secret MinIO (pas `minioadmin`) | `openssl rand -hex 32` |
| `CORS_ORIGINS` | Domaine frontend (pas `*`) | `https://votre-domaine.com` |
| `NEXT_PUBLIC_API_BASE_URL` | URL publique de l'API | `https://votre-domaine.com/api/v1` |

### Variables optionnelles

| Variable | Description |
|----------|-------------|
| `COSIUM_TENANT`, `COSIUM_LOGIN`, `COSIUM_PASSWORD` | Credentials Cosium (lecture seule) |
| `SENTRY_DSN` | Monitoring erreurs Sentry |
| `ANTHROPIC_API_KEY` | Assistants IA |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | Facturation SaaS |

### Validation automatique

L'application refuse de demarrer en `APP_ENV=production` si les secrets par defaut sont utilises. Le validateur dans `backend/app/core/config.py` verifie : JWT_SECRET, S3 credentials, ENCRYPTION_KEY, DATABASE_URL et CORS_ORIGINS.

## 3. Premier deploiement

```bash
# 1. Cloner le repo
git clone <URL_REPO> /opt/optiflow && cd /opt/optiflow

# 2. Configurer l'environnement (voir section 2)
cp .env.example .env
nano .env

# 3. Creer le dossier de backups
mkdir -p backups

# 4. Build et demarrage
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# 5. Attendre que l'API soit prete (~30s)
docker compose -f docker-compose.prod.yml ps

# 6. Executer les migrations
docker compose -f docker-compose.prod.yml exec api alembic upgrade head

# 7. Verifier le health check
curl -f http://localhost/health
```

## 4. Mises a jour

Le script `scripts/deploy.sh` automatise tout le processus :

```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

Le script execute dans l'ordre :
1. Backup automatique de la base de donnees
2. `git pull origin main`
3. Rebuild des images Docker
4. Demarrage des services
5. Attente du health check API (timeout 60s)
6. Migrations Alembic
7. Verification finale via nginx

Pour un deploiement manuel :

```bash
cd /opt/optiflow
git pull origin main
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

## 5. HTTPS / SSL avec Let's Encrypt

### Obtenir le certificat

```bash
# 1. S'assurer que nginx tourne et que le port 80 est accessible
docker compose -f docker-compose.prod.yml up -d nginx

# 2. Lancer certbot
docker compose -f docker-compose.prod.yml run --rm certbot certonly \
    --webroot --webroot-path=/var/www/certbot \
    -d votre-domaine.com --email admin@votre-domaine.com --agree-tos
```

### Activer HTTPS dans nginx

Dans `nginx/nginx.conf`, decommenter le bloc `server` HTTPS (lignes 89-97) et remplacer `your-domain.com` par votre domaine. Ajouter une redirection HTTP vers HTTPS dans le bloc port 80 :

```nginx
# Dans le server port 80, ajouter :
location / {
    return 301 https://$host$request_uri;
}
```

Puis redemarrer nginx :

```bash
docker compose -f docker-compose.prod.yml restart nginx
```

### Renouvellement automatique (cron)

```bash
echo "0 3 * * 1 cd /opt/optiflow && docker compose -f docker-compose.prod.yml run --rm certbot renew && docker compose -f docker-compose.prod.yml restart nginx" | crontab -
```

## 6. Backup & Restore

### Backup manuel

```bash
docker compose -f docker-compose.prod.yml exec -T postgres \
    pg_dump -U optiflow -Fc optiflow > backups/optiflow_$(date +%Y%m%d_%H%M%S).dump
```

### Backup automatique (cron quotidien)

```bash
echo "0 2 * * * cd /opt/optiflow && docker compose -f docker-compose.prod.yml exec -T postgres pg_dump -U optiflow -Fc optiflow > backups/optiflow_\$(date +\%Y\%m\%d).dump && find backups/ -name '*.dump' -mtime +30 -delete" | crontab -
```

### Restore

```bash
# Arreter l'API et le worker
docker compose -f docker-compose.prod.yml stop api worker

# Restaurer
docker compose -f docker-compose.prod.yml exec -T postgres \
    pg_restore -U optiflow -d optiflow --clean --if-exists < backups/optiflow_20260407.dump

# Redemarrer
docker compose -f docker-compose.prod.yml up -d api worker
```

### Backup MinIO (documents)

```bash
docker compose -f docker-compose.prod.yml exec minio \
    mc mirror /data /backup-destination
# Ou simplement sauvegarder le volume Docker minio_data
```

> **Note** : MinIO dans `docker-compose.prod.yml` est prevu pour un deploiement self-hosted.
> Pour une production a grande echelle, utiliser un service S3 manage (AWS S3, OVH Object Storage, etc.)
> et configurer `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` en consequence.

### Worker Celery et Beat

Le worker en production utilise le flag `-B` pour integrer Celery Beat (planificateur de taches).
Cela signifie qu'un seul conteneur `worker` gere a la fois l'execution des taches ET la planification.
C'est le pattern recommande pour les deployments a instance unique.

## 7. Monitoring

### Health checks

| Service | Endpoint / Commande | Intervalle |
|---------|---------------------|------------|
| Nginx | `curl http://localhost/health` | 30s |
| API | `curl http://api:8000/health` (interne) | 30s |
| Frontend | `wget http://web:3000` (interne) | 30s |
| PostgreSQL | `pg_isready` | 10s |
| Redis | `redis-cli ping` | 10s |
| MinIO | `curl http://minio:9000/minio/health/live` | 30s |

### Logs

```bash
# Tous les services
docker compose -f docker-compose.prod.yml logs -f

# Un service specifique
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f worker

# Logs limites (derniere heure)
docker compose -f docker-compose.prod.yml logs --since 1h api
```

Les logs sont limites a 10 Mo / 5 fichiers par container (configure dans docker-compose.prod.yml).

### Sentry (optionnel)

Configurer `SENTRY_DSN` dans `.env` pour recevoir les erreurs en temps reel.

## 8. Rollback

### Rollback du code

```bash
# 1. Identifier le commit precedent
git log --oneline -5

# 2. Revenir au commit precedent
git checkout <COMMIT_SHA>

# 3. Rebuild et redemarrer
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

### Rollback de la base de donnees

```bash
# 1. Downgrade Alembic d'une revision
docker compose -f docker-compose.prod.yml exec api alembic downgrade -1

# 2. Ou restaurer un backup complet (voir section 6)
```

### Rollback complet (code + BDD)

```bash
git checkout <COMMIT_SHA>
docker compose -f docker-compose.prod.yml stop api worker
docker compose -f docker-compose.prod.yml exec -T postgres \
    pg_restore -U optiflow -d optiflow --clean --if-exists < backups/<FICHIER>.dump
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

## 9. Troubleshooting

### L'API refuse de demarrer

```
Configuration invalide pour production
```

Cause : secrets par defaut utilises. Verifier `.env` : JWT_SECRET, S3 keys, ENCRYPTION_KEY, DATABASE_URL.

### PostgreSQL non accessible

```bash
docker compose -f docker-compose.prod.yml logs postgres
docker compose -f docker-compose.prod.yml exec postgres pg_isready -U optiflow
```

Verifier que `POSTGRES_PASSWORD` dans `.env` correspond au mot de passe dans `DATABASE_URL`.

### Erreur 502 Bad Gateway (nginx)

L'API ou le frontend n'est pas encore pret. Verifier :

```bash
docker compose -f docker-compose.prod.yml ps        # tous les services "healthy" ?
docker compose -f docker-compose.prod.yml logs api   # erreurs au demarrage ?
```

### Certificat SSL expire

```bash
docker compose -f docker-compose.prod.yml run --rm certbot renew
docker compose -f docker-compose.prod.yml restart nginx
```

### Worker Celery bloque

```bash
docker compose -f docker-compose.prod.yml restart worker
docker compose -f docker-compose.prod.yml logs worker --tail 50
```

### Espace disque plein

```bash
# Nettoyer les images Docker inutilisees
docker system prune -f

# Verifier les backups anciens
ls -lh backups/
find backups/ -name "*.dump" -mtime +30 -delete
```

### Rate limiting sur /login

Nginx limite a 5 requetes/minute par IP sur `/api/v1/auth/login`. Si un utilisateur est bloque, attendre 1 minute ou ajuster `rate=5r/m` dans `nginx/nginx.conf`.
