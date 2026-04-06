.PHONY: up down build test test-v lint lint-fix typecheck frontend-build check sync backup restore logs shell redis-flush

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose up -d --build

test:
	docker compose exec api pytest -q

test-v:
	docker compose exec api pytest -v

lint:
	docker compose exec api python -m ruff check app/

lint-fix:
	docker compose exec api python -m ruff check app/ --fix

typecheck:
	cd frontend && npx tsc --noEmit

frontend-build:
	cd frontend && rm -rf .next && npx next build

check: lint typecheck test
	@echo "All checks passed!"

sync:
	docker compose exec api python -c "from app.services import erp_sync_service; from app.db.session import SessionLocal; db=SessionLocal(); erp_sync_service.sync_customers(db,1,1); db.close()"

backup:
	./scripts/backup.sh

restore:
	./scripts/restore.sh $(file)

logs:
	docker compose logs -f api

shell:
	docker compose exec api python

redis-flush:
	docker compose exec redis redis-cli FLUSHALL
