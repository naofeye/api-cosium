# Performance — OptiFlow

## Cibles

| Metrique | Cible | Critique si |
|---|---|---|
| Latence p95 API (read) | < 200ms | > 500ms |
| Latence p95 API (write) | < 500ms | > 1s |
| Latence p99 API | < 1s | > 2s |
| Throughput soutenu | 100 req/s | < 30 req/s |
| Time to interactive frontend | < 2s | > 5s |
| Lighthouse Performance | >= 90 | < 70 |

## Stack tuning

### PostgreSQL

```yaml
# docker-compose.yml command:
postgres:
  command: >
    postgres
    -c max_connections=150
    -c idle_in_transaction_session_timeout=60000
    -c statement_timeout=180000
    -c log_min_duration_statement=500
```

Pool SQLAlchemy (`db/session.py`) :
- `pool_size=50`
- `max_overflow=50`
- `pool_recycle=1800`
- `pool_pre_ping=True`
- `statement_timeout=30000` API / `120000` Celery

### Redis

```yaml
redis:
  command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

### Celery

- 5 queues isolees : `default`, `email`, `sync`, `extraction`, `batch`, `reminder`
- `acks_late=True` + `reject_on_worker_lost=True`
- `soft_time_limit=300s`, `hard_time_limit=360s`
- `result_expires=86400s` (cleanup auto Redis)

### Nginx

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=60r/s;
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
client_max_body_size 25M;
```

## N+1 patterns a eviter

```python
# ❌ N+1 : 1 query par customer
for c in db.scalars(select(Customer)).all():
    cases = c.cases  # lazy load → query par customer

# ✅ Eager loading
customers = db.scalars(
    select(Customer).options(selectinload(Customer.cases))
).all()
```

Audit : `app/services/erp_sync_*.py` utilise des `existing_map` pre-chargees pour eviter N+1 sur upsert.

## Pagination obligatoire

Tout endpoint qui peut retourner > 100 items DOIT etre pagine :
```python
page: int = Query(1, ge=1)
page_size: int = Query(25, ge=1, le=100)
offset = (page - 1) * page_size
```

`PaginatedResponse[T]` (`schemas/common.py`) standardise la reponse.

## Cache Redis

```python
from app.core.redis_cache import cache_get, cache_set

cached = cache_get(f"admin:metrics:{tenant_id}")
if cached:
    return MetricsResponse(**cached)

result = compute_expensive(db, tenant_id)
cache_set(f"admin:metrics:{tenant_id}", result.model_dump(), ttl=300)
```
TTL recommandes :
- Metrics dashboard : 5 min (300s)
- Cosium reference data : 1h (3600s)
- Search results : non-cache (toujours fresh)

## Frontend

### Bundle size

```bash
cd apps/web
npx @next/bundle-analyzer
```
Cible : initial JS < 200kb gzipped.

### Code splitting

```typescript
// Lazy load Recharts (lourd)
const DashboardCharts = dynamic(
  () => import("./components/DashboardCharts"),
  { ssr: false, loading: () => <SkeletonCard /> }
);
```

### SWR cache

```typescript
useSWR(key, fetcher, {
  revalidateOnFocus: false,    // anti spam onfocus
  refreshInterval: 60000,       // refresh 1min pour KPIs
  dedupingInterval: 2000,       // dedup requetes < 2s
});
```

## Profiling

### Backend (cProfile)

```bash
docker compose exec api python -m cProfile -o /tmp/profile.out -m pytest tests/test_xxx.py
docker compose exec api python -c "import pstats; p = pstats.Stats('/tmp/profile.out'); p.sort_stats('cumulative').print_stats(30)"
```

### py-spy (live)

```bash
docker compose exec api pip install py-spy
docker compose exec api py-spy record -o /tmp/profile.svg --pid <api_pid>
```

### Frontend (Lighthouse CI)

```bash
cd apps/web
npx lhci autorun
```

## Observabilite

Voir `docs/CELERY.md` (Flower), `docker-compose.monitoring.yml` (Prometheus + Grafana).

Endpoint Prometheus : `/api/v1/metrics` (exposition texte standard).

## Cas connus

- **Sync Cosium produits** : limite a 50 (catalog 398k, sample only)
- **Sync Cosium paiements** : `full=True` une fois par semaine (off-hours), incremental sinon
- **Export 50k+ rows** : utiliser streaming (`StreamingResponse`) pas tout en memoire
- **Upload >25MB** : refuse par nginx (aligne `MAX_UPLOAD_SIZE_MB=20`)

## Quand scaler

Symptomes -> action :
- Latence p95 > 500ms : audit slow queries + ajouter index
- Pool DB exhausted : augmenter `max_connections` PostgreSQL ou ajouter PgBouncer
- Queue Celery monte : `--scale worker=3` (concurrency par defaut 4 = 12 tasks parallel)
- Disque MinIO > 80% : ajouter volume ou archiver vieux documents (S3 cold storage)
