# Alembic — migrations BDD OptiFlow

> Toute modification de schema PostgreSQL passe par Alembic. Jamais `Base.metadata.create_all()` en prod.

## Workflow

### 1. Modifier un modele SQLAlchemy
```python
# apps/api/app/models/customer.py
class Customer(Base):
    new_field: Mapped[str | None] = mapped_column(String(100), nullable=True)
```

### 2. Generer la migration auto
```bash
make migration MSG="add new_field to customer"
# = docker compose exec api alembic revision --autogenerate -m "..."
```
Cree `apps/api/alembic/versions/<hash>_add_new_field_to_customer.py`.

### 3. Verifier le diff genere
- Lire le `upgrade()` : create_table, add_column, create_index ?
- Lire le `downgrade()` : doit etre l'**inverse exact** (drop_column, drop_index)
- Pas de logique metier dans la migration (pas de UPDATE/INSERT data)
- Si DROP COLUMN : ajouter `op.add_column(...)` dans downgrade pour reverse

### 4. Appliquer
```bash
make migrate              # alembic upgrade head
```

### 5. Verifier rollback
```bash
docker compose exec api alembic downgrade -1
docker compose exec api alembic upgrade head
```
**CI fait ce test automatiquement** (`backend-tests` job).

## Commandes courantes

| Action | Commande |
|---|---|
| Statut courant | `alembic current` |
| Historique | `alembic history --verbose` |
| Aller a head | `alembic upgrade head` |
| Reculer d'un cran | `alembic downgrade -1` |
| Reculer a une revision | `alembic downgrade <hash>` |
| Aller a une revision precise | `alembic upgrade <hash>` |
| Generer SQL sans appliquer | `alembic upgrade head --sql` |
| Auto-generate diff | `alembic revision --autogenerate -m "msg"` |
| Migration vide (data manuelle) | `alembic revision -m "msg"` |

## Patterns obligatoires

### DDL non-bloquant
PostgreSQL bloque les ALTER TABLE. Pour grosses tables (>1M rows) :
```python
def upgrade() -> None:
    # OUI : ajouter une colonne nullable est rapide
    op.add_column("customers", sa.Column("new_field", sa.String(100), nullable=True))

    # NON : NOT NULL sur grosse table = lock long
    # op.add_column("customers", sa.Column("new_field", sa.String(100), nullable=False))

    # OUI : si NOT NULL requis, faire en 3 etapes (3 migrations) :
    # 1. add nullable
    # 2. backfill via UPDATE en batch
    # 3. ALTER COLUMN SET NOT NULL
```

### Index CONCURRENTLY (postgres only)
```python
def upgrade() -> None:
    op.execute("COMMIT")  # sortir de la transaction
    op.execute("CREATE INDEX CONCURRENTLY ix_customers_email ON customers(email)")

def downgrade() -> None:
    op.execute("COMMIT")
    op.execute("DROP INDEX CONCURRENTLY IF EXISTS ix_customers_email")
```
**Note** : CONCURRENTLY ne peut pas tourner dans une transaction.

### Data migration
A bannir dans la mesure du possible. Si necessaire :
```python
def upgrade() -> None:
    # 1. DDL d'abord
    op.add_column("customers", sa.Column("status", sa.String(20)))

    # 2. Backfill via SQL pur (pas d'ORM — schemas peuvent differer)
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE customers SET status = 'active'"))
```

## Anti-patterns INTERDITS

```python
# ❌ Pas d'import ORM dans une migration (la classe peut avoir change)
from app.models import Customer
db.query(Customer).update(...)

# ✅ SQL direct via op.execute
op.execute("UPDATE customers SET status = 'active'")

# ❌ Pas de logique metier (validation, calculs)
def upgrade() -> None:
    customers = db.query(Customer).all()
    for c in customers:
        c.score = compute_score(c)  # NON : trop complexe pour migration

# ✅ Migration DDL pure, backfill via tache Celery one-shot ensuite
```

## Branching et conflits

Si 2 PRs creent simultanement une migration depuis la meme parent, conflit :
```bash
alembic heads          # plusieurs heads detectees
alembic merge -m "merge migration A and B" <hash_A> <hash_B>
```
Cree une revision de merge qui pointe les 2 parents.

## Rollback en production (procedure)

1. Identifier la migration fautive : `alembic current`
2. Backup BDD : `make backup`
3. Downgrade : `docker compose exec api alembic downgrade <hash_avant>`
4. Verifier : `alembic current` retourne le hash visee
5. Restart API : `docker compose restart api worker`
6. Si la migration etait deja deployee depuis longtemps avec ecritures recentes,
   evaluer si downgrade efface des donnees (lire le `downgrade()` du fichier)

Si downgrade impossible (drop column avec donnees) :
- Restore du backup BDD : `./scripts/restore_db.sh ...`
- Cf `docs/RUNBOOK.md` pour la procedure de rollback complete

## Tests CI

Le job `backend-tests` execute :
```yaml
- alembic upgrade head     # applique tout
- alembic downgrade -1     # rollback derniere
- alembic upgrade head     # re-applique → valide reversibilite
```
Fail si la derniere migration n'est pas reversible (ex : DROP TABLE sans recreate).
