# RUNBOOK — Incidents production OptiFlow

> Procedures pour l'oncall. Si tu n'es pas oncall : ne touche a rien sans accord.

## Triage rapide (< 5 min)

```bash
# 1. Tous les services up ?
docker compose ps

# 2. Health endpoint
curl -s https://app.optiflow.example.com/api/v1/admin/health | jq

# 3. Sentry derniers events
open https://sentry.io/organizations/optiflow/issues/?statsPeriod=1h

# 4. Logs API en live
make logs FILTER=api
```

Niveau severity :
- **P1** (degradation totale) : page tout le monde, < 15min response
- **P2** (degradation partielle) : un domaine touche, < 1h response
- **P3** (incident isole) : 1 client/feature, traiter dans la journee

## Incidents courants

### API ne demarre pas

```bash
docker compose logs api | tail -50
```
- `JWT_SECRET` non defini en prod -> verifier `.env`
- Migration alembic pendante -> `docker compose exec api alembic upgrade head`
- Connexion DB refusee -> verifier `postgres` up + `DATABASE_URL` correct

### Latence API > 2s

```bash
# Slow queries
docker compose exec postgres psql -U optiflow -c \
  "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Pool exhaustion ?
docker compose exec postgres psql -U optiflow -c \
  "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"
```
Actions :
- > 100 connexions actives : restart api (`docker compose restart api`)
- Slow query identifiee : ajouter index (cf docs/DATABASE_INDEXES.md)
- Pool epuise : verifier qu'aucune transaction ne reste ouverte

### Queue Celery monte

```bash
docker compose exec api celery -A app.tasks inspect active
docker compose exec api celery -A app.tasks inspect reserved
```
Actions :
- Worker crashe : `docker compose restart worker`
- Tache en boucle : `celery -A app.tasks control revoke <task_id>`
- Backlog important : scaler workers `docker compose up -d --scale worker=3`

### Sync Cosium echoue

```bash
# Verifier credentials
docker compose exec api python -c "
from app.services.erp_auth_service import _get_connector_for_tenant, _authenticate_connector
from app.db.session import SessionLocal
db = SessionLocal()
c, t = _get_connector_for_tenant(db, 1)
_authenticate_connector(c, t)
print('OK')
"
```
Actions :
- Cookie expire : utilisateur doit renouveler (cf docs/COSIUM_AUTH.md)
- Cosium down : attendre, mettre banner UI
- Erreur 5xx repete : Sentry alert + ticket

### MinIO refuse les uploads

```bash
docker compose logs minio | tail -30
curl -I http://localhost:9000/minio/health/live
```
- Disque plein : `df -h /var/lib/docker/volumes/`, nettoyer ou augmenter
- Bucket inexistant : recreer via console (http://localhost:9001)

## Restoration backup (perte de donnees)

1. **Stop l'API** : `docker compose stop api worker beat`
2. **Lister backups** : `ls -lh runtime/backups/`
3. **Dry-run** : `./scripts/restore_db.sh --dry-run runtime/backups/optiflow_<date>.dump`
4. **Restore** (cree backup pre-restore auto) : `./scripts/restore_db.sh runtime/backups/optiflow_<date>.dump`
5. **Restart** : `docker compose start api worker beat`
6. **Verifier** : login UI + sync test

## Rollback deploy

```bash
git log --oneline -10               # identifier commit stable
git reset --hard <commit_stable>
./scripts/deploy.sh
```
Si migration cassante : `./scripts/restore_db.sh runtime/backups/pre-restore_<date>.dump`

## Rotation secrets

```bash
# Generer nouveau JWT_SECRET
python -c "import secrets; print(secrets.token_urlsafe(64))"

# 1. Mettre a jour .env
# 2. Restart API : tous les tokens existants sont invalides
# 3. Tous les utilisateurs doivent re-login
```

Pour ENCRYPTION_KEY : ne JAMAIS rotater sans script de re-encrypt des donnees existantes.

## Checklist post-incident

- [ ] Probleme resolu et verifie en prod
- [ ] Sentry incident close
- [ ] Cause racine identifiee
- [ ] Postmortem ecrit (5 Why) si P1/P2
- [ ] Action items pour eviter recurrence
- [ ] Mise a jour de ce RUNBOOK si nouvelle procedure decouverte
- [ ] Communication client/equipe si downtime > 5 min

## Contacts urgence

- Hosting : <provider>
- DBA backup : <contact>
- Security : security@optiflow.ai
