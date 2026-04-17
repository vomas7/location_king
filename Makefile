.PHONY: dev dev-d prod down down-v logs logs-backend ps \
        shell-backend shell-db shell-redis migrate migration

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

dev-d:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d

prod:
	docker compose up --build -d

down:
	docker compose down

down-v:
	docker compose down -v

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-db:
	docker compose logs -f db

ps:
	docker compose ps

# ─── Shells (доступны после: ssh -L порт:localhost:порт user@server) ───
shell-backend:
	docker compose exec backend bash

shell-db:
	docker compose exec db psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}

shell-redis:
	docker compose exec redis redis-cli -a $${REDIS_PASSWORD}

# ─── Миграции ─────────────────────────────────────────────────────────
migrate:
	docker compose exec backend alembic upgrade head

# Использование: make migration msg="add leaderboard table"
migration:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

rollback:
	docker compose exec backend alembic downgrade -1

# ─── Линтинг и форматирование ────────────────────────────────────────
lint:
	cd backend && ruff check .

format:
	cd backend && ruff format .

fix:
	cd backend && ruff check --fix .

lint-all: lint format fix

# Запуск линтинга локально (без Docker)
lint-local:
	./lint_and_fix.sh
