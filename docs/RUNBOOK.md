# RUNBOOK — Incidents production OptiFlow

> Procedures pour l'oncall. Si tu n'es pas oncall : ne touche a rien sans accord.

## SLO (objectifs)

| Indicateur | Cible | Mesure |
|---|---|---|
| Disponibilite (uptime) | 99.5% / mois (~3h45 indispo max) | Endpoint `/api/v1/health` 1xx |
| Latence p95 API | < 500ms | Sentry performance |
| Latence p99 API | < 2s | Sentry performance |
| Taux d'erreur HTTP 5xx | < 0.5% | Sentry events / requests |
| Sync Cosium reussie | > 95% des runs | Logs `cosium_sync_completed` vs `cosium_sync_failed` |
| Backup BDD | quotidien, < 24h | `scripts/backup_offsite.sh` cron |

Ecart prolonge SLO -> declencher revue post-mortem (cf section "Post-mortem").

## Severity & escalade

- **P1** (degradation totale, perte de donnees imminente) : alerter Nabil immediat (telephone), < 15min response, communiquer toutes les 15min
- **P2** (degradation partielle, un domaine touche) : alerter Nabil, < 1h response, communiquer toutes les heures
- **P3** (incident isole, 1 client/feature) : ouvrir issue, traiter dans la journee

Triage > 30 min sans progression P1/P2 = remonter a Nabil pour decision (rollback, communication client).

## Triage rapide (< 5 min)

```bash
# 1. Tous les services up ?
docker compose ps

# 2. Health endpoint (remplacer par le domaine reel en prod)
curl -s https://cosium.ia.coging.com/api/v1/health | jq

# 3. Sentry derniers events (configurer SENTRY_DSN en prod ; si vide, sentry off)
# Lien Sentry projet à completer ici une fois `SENTRY_DSN` configure.

# 4. Logs API en live
make logs FILTER=api
```

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

### Rollback DB complet

Quand le rollback applicatif ne suffit pas (donnees corrompues, migration cassante avec pertes) :

```bash
# 1. Stopper toute l'app pour eviter de nouvelles ecritures
docker compose stop api worker beat web

# 2. Identifier le dernier backup pre-incident (avant la migration cassante)
ls -lht runtime/backups/optiflow_*.dump | head -10

# 3. Dry-run restore pour valider le fichier
./scripts/restore_db.sh --dry-run runtime/backups/optiflow_<date>.dump

# 4. Pre-restore backup automatique (au cas ou) puis restore reel
./scripts/restore_db.sh runtime/backups/optiflow_<date>.dump

# 5. Si la version applicative actuelle est >= a la version BDD restoree,
#    rollback aussi le code a un commit anterieur a la migration :
git log --oneline --all -- apps/api/alembic/versions/  | head -5
git reset --hard <commit_avant_migration_cassante>

# 6. Redemarrer
docker compose start api worker beat web

# 7. Smoke test : login + lister clients + sync test
```

Communique le rollback aux utilisateurs : la BDD est en arriere de N heures,
toute donnee creee/modifiee depuis le backup est PERDUE. Restorer manuellement
les donnees critiques apres analyse des logs.

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
