# Celery — retry policy et operations

## Architecture

- **Broker** : Redis (`redis://redis:6379/0`)
- **Backend** : Redis (résultats des tâches)
- **Worker** : `celery -A app.tasks worker --loglevel=info`
- **Beat** : `celery -A app.tasks beat --schedule=/tmp/celerybeat-schedule`

## Retry par défaut

| Paramètre | Valeur | Justification |
|-----------|--------|---------------|
| `autoretry_for` | `(Exception,)` sur tâches IO (Cosium, email, Stripe) | Catch large, filtré par backoff |
| `retry_backoff` | `True` (exponential) | 2s → 4s → 8s → 16s |
| `retry_backoff_max` | `300s` (5 min) | Évite les retries trop longs |
| `retry_jitter` | `True` | Évite thundering herd |
| `max_retries` | `5` | Au-delà, tâche en DLQ |
| `acks_late` | `True` | Pas d'ack tant que non traité (résilience crash) |

## Convention par type de tâche

```python
# Tâche IO externe (Cosium, email, Stripe) : retry agressif
@shared_task(bind=True, autoretry_for=(httpx.HTTPError, TimeoutError),
             retry_backoff=True, retry_backoff_max=300, max_retries=5)
def sync_cosium_customers(self, tenant_id: int) -> None: ...

# Tâche pure (calcul, DB) : pas de retry auto (les erreurs sont des bugs)
@shared_task(bind=True)
def build_reconciliation_report(self, tenant_id: int) -> None: ...

# Tâche batch : retry limité, progression visible
@shared_task(bind=True, autoretry_for=(Exception,), max_retries=3)
def batch_process_pec(self, batch_id: int) -> None:
    # Update status tous les 100 items
    ...
```

## Idempotence obligatoire

Toute tâche doit être **idempotente** — un re-run ne doit pas créer de doublons.

```python
# BON : EXISTS avant INSERT
def create_notification(tenant_id: int, user_id: int, entity_id: int, entity_type: str):
    exists = db.query(Notification).filter_by(
        tenant_id=tenant_id, user_id=user_id,
        entity_id=entity_id, entity_type=entity_type,
        created_at__gte=today,
    ).first()
    if exists:
        return
    db.add(Notification(...))

# INTERDIT : insert aveugle
def create_notification(...):
    db.add(Notification(...))  # si la tâche re-run, 2 notifs !
```

## Dead-letter queue

Les tâches qui dépassent `max_retries` sont envoyées dans la queue `dlq` pour analyse.

```python
# tasks/__init__.py
def task_failure_handler(sender, task_id, exception, args, kwargs, traceback, einfo, **kw):
    logger.error("task_dlq", task=sender.name, task_id=task_id, error=str(exception))
    # Sentry capture + notification admin
```

## Beat schedule

Les tâches planifiées dans `app/tasks/schedule.py` :

| Tâche | Fréquence | Description |
|-------|-----------|-------------|
| `sync_cosium_customers` | 1h | Incrémental depuis last_sync |
| `send_reminder_emails` | 9h du lundi-vendredi | Relances programmées |
| `pec_auto_relance_30d` | 1j (8h) | Alerte PEC > 30j sans réponse |
| `cleanup_blacklisted_tokens` | 6h | Purge JWT expirés |
| `weekly_analytics_rollup` | dim 2h | Agrégats stats hebdo |

## Monitoring

- **Flower** (dev) : `http://localhost:5555` — visualiser queues et workers
- **Prometheus** : `/metrics` expose `celery_tasks_total`, `celery_task_duration_seconds`
- **Sentry** : erreurs capturées automatiquement via `celery_sentry_init`

## Commandes utiles

```bash
# Purger toutes les tâches
docker compose exec api celery -A app.tasks purge

# Inspecter les workers actifs
docker compose exec api celery -A app.tasks inspect active

# Revoquer une tâche par ID
docker compose exec api celery -A app.tasks control revoke <task_id>

# Lancer une tâche manuellement (debug)
docker compose exec api python -c "from app.tasks.sync_tasks import sync_cosium_customers; sync_cosium_customers.delay(tenant_id=1)"
```

## Troubleshooting

| Symptôme | Cause probable | Action |
|----------|----------------|--------|
| Queue Celery monte | Worker lent ou crashé | `docker compose logs worker`, scaler `--concurrency=4` |
| Même tâche retry en boucle | Erreur permanente (bug) | Regarder Sentry, pas juste relancer |
| Beat ne déclenche pas | Clock skew ou schedule corrompu | Supprimer `/tmp/celerybeat-schedule`, redémarrer |
| Tâche timeout | `statement_timeout` PG atteint (120s) | Découper en batch, optimiser requête |
