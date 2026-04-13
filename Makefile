.PHONY: help dev up down logs ps build rebuild restart \
        api-shell db-shell web-shell shell \
        test test-api test-web lint lint-api lint-web lint-fix typecheck check \
        migrate migration seed sync redis-flush \
        backup restore deploy \
        frontend-build clean prune

# Couleur (terminal supportant ANSI)
BLUE := \033[36m
RESET := \033[0m

help: ## Affiche cette aide
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BLUE)%-15s$(RESET) %s\n", $$1, $$2}'

# === Lifecycle ===

dev: ## Demarre la stack de dev (build + up)
	docker compose up -d --build

up: ## Demarre tous les services
	docker compose up -d

down: ## Stoppe tous les services
	docker compose down

logs: ## Suit les logs (FILTER=api pour filtrer)
	docker compose logs -f $(FILTER)

ps: ## Etat des services
	docker compose ps

build: ## Build les images
	docker compose build

rebuild: ## Rebuild force (no cache)
	docker compose build --no-cache

restart: ## Restart api + worker + beat (apres modif code)
	docker compose restart api worker beat

# === Shells ===

api-shell: ## Bash dans le container API
	docker compose exec api bash

db-shell: ## psql dans postgres
	docker compose exec postgres psql -U optiflow -d optiflow

web-shell: ## Shell dans le container web
	docker compose exec web sh

shell: ## REPL Python dans l'API
	docker compose exec api python

# === Tests & qualite ===

test: test-api test-web ## Lance tous les tests

test-api: ## Tests pytest backend
	docker compose exec -T api pytest tests/ -v --tb=short

test-web: ## Tests vitest frontend
	docker compose exec -T web npm run test -- --run

lint: lint-api lint-web ## Lint complet

lint-api: ## Ruff backend
	docker compose exec -T api ruff check app/

lint-web: ## ESLint frontend
	docker compose exec -T web npm run lint

lint-fix: ## Ruff --fix
	docker compose exec api python -m ruff check app/ --fix

typecheck: ## TypeScript strict
	cd apps/web && npx tsc --noEmit

check: lint typecheck test-api ## Lint + typecheck + tests backend
	@echo "All checks passed."

# === Migrations ===

migrate: ## Applique les migrations Alembic
	docker compose exec -T api alembic upgrade head

migration: ## Cree une migration (MSG="description")
	@test -n "$(MSG)" || (echo "Usage: make migration MSG=\"description\"" && exit 1)
	docker compose exec -T api alembic revision --autogenerate -m "$(MSG)"

seed: ## Re-seed des donnees demo
	docker compose exec -T api python -m app.seed

# === Operations ===

sync: ## Sync manuel customers Cosium (tenant 1)
	docker compose exec api python -c "from app.services import erp_sync_service; from app.db.session import SessionLocal; db=SessionLocal(); erp_sync_service.sync_customers(db,1,1); db.close()"

redis-flush: ## Vide le cache Redis (DEV uniquement)
	docker compose exec redis redis-cli FLUSHALL

# === Build & deploy ===

frontend-build: ## Build prod du frontend
	cd apps/web && rm -rf .next && npx next build

backup: ## Backup BDD
	./scripts/backup_db.sh

restore: ## Restore BDD (file=path/to/backup.dump)
	@test -n "$(file)" || (echo "Usage: make restore file=runtime/backups/optiflow_*.dump" && exit 1)
	./scripts/restore_db.sh docker-compose.yml $(file)

deploy: ## Deploiement production (utilise docker-compose.prod.yml)
	./scripts/deploy.sh

# === Nettoyage ===

clean: ## Stoppe et supprime volumes (DESTRUCTIF)
	docker compose down -v

prune: ## Nettoie images/volumes Docker non utilises (DESTRUCTIF)
	docker system prune -af --volumes
