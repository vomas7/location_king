.PHONY: dev prod down logs ps shell-backend shell-db

# ─── Разработка ───────────────────────────────────────────────
dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

dev-d:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d

# ─── Продакшн ─────────────────────────────────────────────────
prod:
	docker compose up --build -d

# ─── Остановка ────────────────────────────────────────────────
down:
	docker compose down

down-v:
	docker compose down -v  # + удалить volumes (осторожно!)

# ─── Логи ─────────────────────────────────────────────────────
logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-db:
	docker compose logs -f db

# ─── Статус ───────────────────────────────────────────────────
ps:
	docker compose ps

# ─── Shells ───────────────────────────────────────────────────
shell-backend:
	docker compose exec backend bash

shell-db:
	docker compose exec db psql -U $${POSTGRES_USER} -d $${POSTGRES_DB}

shell-redis:
	docker compose exec redis redis-cli -a $${REDIS_PASSWORD}

# ─── Миграции ─────────────────────────────────────────────────
migrate:
	docker compose exec backend alembic upgrade head

migration:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"
